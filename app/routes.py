"""Web routes for the tournament application."""

from datetime import date, datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from urllib.parse import urlparse

from .extensions import db
from .fixture_engine import MAX_TEAMS, generate_knockout_bracket
from .models import Match, Player, Team, Tournament
from .result_engine import (
    ResultValidationError,
    complete_match,
    parse_score,
    save_tied_result,
    set_match_in_progress,
)


main_bp = Blueprint("main", __name__)
SPORTS = (
    "Football",
    "Cricket",
    "Basketball",
    "Volleyball",
    "Badminton",
    "Tennis",
    "Other",
)
STATUSES = ("upcoming", "active", "completed")
STATUS_LABELS = {"upcoming": "Upcoming", "active": "Active", "completed": "Completed"}
MATCH_STATUS_LABELS = {
    "scheduled": "Scheduled",
    "ready": "Ready",
    "in_progress": "In Progress",
    "completed": "Completed",
    "pending": "Scheduled",
    "bye": "Completed",
}


@main_bp.get("/")
def home():
    """Render the database-backed dashboard."""

    dashboard_error = None
    stats = {
        "total_tournaments": 0,
        "active_tournaments": 0,
        "completed_tournaments": 0,
        "total_teams": 0,
    }
    recent_tournaments = []

    try:
        stats["total_tournaments"] = db.session.query(func.count(Tournament.id)).scalar() or 0
        stats["active_tournaments"] = (
            db.session.query(func.count(Tournament.id))
            .filter(Tournament.status == "active")
            .scalar()
            or 0
        )
        stats["completed_tournaments"] = (
            db.session.query(func.count(Tournament.id))
            .filter(Tournament.status == "completed")
            .scalar()
            or 0
        )
        stats["total_teams"] = db.session.query(func.count(Team.id)).scalar() or 0
        recent_tournaments = (
            Tournament.query.order_by(Tournament.created_at.desc()).limit(8).all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        dashboard_error = "Dashboard data is temporarily unavailable. Please try again."

    return render_template(
        "index.html",
        title="Dashboard",
        stats=stats,
        recent_tournaments=recent_tournaments,
        dashboard_error=dashboard_error,
    )


@main_bp.route("/tournaments", methods=["GET"])
def tournaments():
    """List tournaments with optional name, sport, and status filters."""

    search = request.args.get("search", "").strip()
    sport = request.args.get("sport", "").strip()
    status = request.args.get("status", "").strip().lower()
    query = Tournament.query

    if search:
        query = query.filter(Tournament.name.ilike(f"%{search}%"))
    if sport in SPORTS:
        query = query.filter(Tournament.sport == sport)
    else:
        sport = ""
    if status in STATUSES:
        query = query.filter(Tournament.status == status)
    else:
        status = ""

    tournament_list = query.order_by(Tournament.created_at.desc()).all()
    return render_template(
        "tournaments.html",
        title="Tournaments",
        tournaments=tournament_list,
        sports=SPORTS,
        statuses=STATUS_LABELS,
        filters={"search": search, "sport": sport, "status": status},
    )


@main_bp.route("/tournaments/new", methods=["GET", "POST"])
def new_tournament():
    """Create a tournament after validating all required fields."""

    form_data = _form_data()
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_tournament_form(form_data)
        if not errors:
            tournament = Tournament(**cleaned_data)
            try:
                db.session.add(tournament)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The tournament could not be saved. Please try again."
            else:
                flash(f"{tournament.name} was created successfully.", "success")
                return redirect(url_for("main.tournament_detail", tournament_id=tournament.id))

    return render_template(
        "tournament_form.html",
        title="Create Tournament",
        heading="Create tournament",
        eyebrow="Tournament workspace",
        form_data=form_data,
        errors=errors,
        sports=SPORTS,
        statuses=STATUS_LABELS,
        submit_label="Create tournament",
    ), 400 if errors else 200


@main_bp.route("/tournaments/<int:tournament_id>/edit", methods=["GET", "POST"])
def edit_tournament(tournament_id):
    """Edit an existing tournament and persist the changes."""

    tournament = db.get_or_404(Tournament, tournament_id)
    form_data = _tournament_form_data(tournament) if request.method == "GET" else _form_data()
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_tournament_form(form_data)
        if not errors:
            for field, value in cleaned_data.items():
                setattr(tournament, field, value)
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The tournament could not be updated. Please try again."
            else:
                flash(f"{tournament.name} was updated successfully.", "success")
                return redirect(url_for("main.tournament_detail", tournament_id=tournament.id))

    return render_template(
        "tournament_form.html",
        title="Edit Tournament",
        heading="Edit tournament",
        eyebrow="Tournament workspace",
        form_data=form_data,
        errors=errors,
        sports=SPORTS,
        statuses=STATUS_LABELS,
        submit_label="Save changes",
        tournament=tournament,
    ), 400 if errors else 200


@main_bp.post("/tournaments/<int:tournament_id>/delete")
def delete_tournament(tournament_id):
    """Delete a tournament and its owned teams, players, and matches transactionally."""

    tournament = db.get_or_404(Tournament, tournament_id)
    tournament_name = tournament.name
    try:
        tournament.champion_id = None
        db.session.delete(tournament)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The tournament could not be deleted. No changes were made.", "error")
        return redirect(url_for("main.tournament_detail", tournament_id=tournament_id))
    flash(f"{tournament_name} and its associated records were deleted.", "success")
    return redirect(url_for("main.tournaments"))


@main_bp.get("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    """Show tournament details, teams, and management actions."""

    tournament = db.get_or_404(Tournament, tournament_id)
    return render_template(
        "tournament_detail.html", title=tournament.name, tournament=tournament
    )


@main_bp.route("/teams", methods=["GET"])
def teams():
    """List teams with optional name and tournament filters."""

    search = request.args.get("search", "").strip()
    tournament_id_value = request.args.get("tournament_id", "").strip()
    query = Team.query.join(Tournament, Team.tournament_id == Tournament.id)
    if search:
        query = query.filter(Team.name.ilike(f"%{search}%"))
    try:
        tournament_id = int(tournament_id_value) if tournament_id_value else None
    except ValueError:
        tournament_id = None
        tournament_id_value = ""
    if tournament_id:
        query = query.filter(Team.tournament_id == tournament_id)
    else:
        tournament_id_value = ""

    return render_template(
        "teams.html",
        title="Teams",
        teams=query.order_by(Team.name.asc()).all(),
        tournaments=Tournament.query.order_by(Tournament.name.asc()).all(),
        filters={"search": search, "tournament_id": tournament_id_value},
    )


@main_bp.route("/teams/new", methods=["GET", "POST"])
def new_team():
    """Register a team in an existing tournament."""

    form_data = _team_form_data()
    if request.method == "GET" and request.args.get("tournament_id"):
        form_data["tournament_id"] = request.args.get("tournament_id", "")
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_team_form(form_data)
        if not errors:
            team = Team(**cleaned_data)
            try:
                db.session.add(team)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["name"] = "A team with this name already exists in the selected tournament."
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The team could not be saved. Please try again."
            else:
                flash(f"{team.name} was registered successfully.", "success")
                return redirect(url_for("main.team_detail", team_id=team.id))

    return render_template(
        "team_form.html",
        title="Register Team",
        heading="Register team",
        eyebrow="Team management",
        form_data=form_data,
        errors=errors,
        tournaments=Tournament.query.order_by(Tournament.name.asc()).all(),
        submit_label="Register team",
    ), 400 if errors else 200


@main_bp.route("/teams/<int:team_id>/edit", methods=["GET", "POST"])
def edit_team(team_id):
    """Edit team details and persist changes."""

    team = db.get_or_404(Team, team_id)
    form_data = _team_form_data(team) if request.method == "GET" else _team_form_data()
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_team_form(form_data, current_team=team)
        if not errors:
            for field, value in cleaned_data.items():
                setattr(team, field, value)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["name"] = "A team with this name already exists in the selected tournament."
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The team could not be updated. Please try again."
            else:
                flash(f"{team.name} was updated successfully.", "success")
                return redirect(url_for("main.team_detail", team_id=team.id))

    return render_template(
        "team_form.html",
        title="Edit Team",
        heading="Edit team",
        eyebrow="Team management",
        form_data=form_data,
        errors=errors,
        tournaments=Tournament.query.order_by(Tournament.name.asc()).all(),
        submit_label="Save changes",
        team=team,
    ), 400 if errors else 200


@main_bp.post("/teams/<int:team_id>/delete")
def delete_team(team_id):
    """Delete a team and its players while preserving fixtures without orphaned team references."""

    team = db.get_or_404(Team, team_id)
    team_name = team.name
    try:
        for match in team.home_matches:
            match.home_team_id = None
        for match in team.away_matches:
            match.away_team_id = None
        db.session.query(Match).filter(Match.winner_id == team.id).update(
            {Match.winner_id: None}, synchronize_session=False
        )
        db.session.query(Tournament).filter(Tournament.champion_id == team.id).update(
            {Tournament.champion_id: None}, synchronize_session=False
        )
        db.session.delete(team)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The team could not be deleted. No changes were made.", "error")
        return redirect(url_for("main.team_detail", team_id=team_id))

    flash(f"{team_name} and its players were deleted.", "success")
    return redirect(url_for("main.teams"))


@main_bp.get("/teams/<int:team_id>")
def team_detail(team_id):
    """Show a team, its tournament, captain, and registered players."""

    team = db.get_or_404(Team, team_id)
    return render_template("team_detail.html", title=team.name, team=team)


@main_bp.route("/players", methods=["GET"])
def players():
    """List players with optional name and team filters."""

    search = request.args.get("search", "").strip()
    team_id_value = request.args.get("team_id", "").strip()
    query = Player.query.join(Team).join(Tournament, Team.tournament_id == Tournament.id)
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))
    try:
        team_id = int(team_id_value) if team_id_value else None
    except ValueError:
        team_id = None
        team_id_value = ""
    if team_id:
        query = query.filter(Player.team_id == team_id)
    else:
        team_id_value = ""

    return render_template(
        "players.html",
        title="Players",
        players=query.order_by(Player.name.asc()).all(),
        teams=Team.query.join(Tournament, Team.tournament_id == Tournament.id).order_by(Team.name.asc()).all(),
        filters={"search": search, "team_id": team_id_value},
    )


@main_bp.route("/players/new", methods=["GET", "POST"])
def new_player():
    """Register a player under an existing team."""

    form_data = _player_form_data()
    if request.method == "GET" and request.args.get("team_id"):
        form_data["team_id"] = request.args.get("team_id", "")
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_player_form(form_data)
        if not errors:
            player = Player(**cleaned_data)
            try:
                db.session.add(player)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["jersey_number"] = "That jersey number is already used by this team."
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The player could not be saved. Please try again."
            else:
                flash(f"{player.name} was registered successfully.", "success")
                return redirect(url_for("main.player_detail", player_id=player.id))

    return render_template(
        "player_form.html",
        title="Register Player",
        heading="Register player",
        eyebrow="Player management",
        form_data=form_data,
        errors=errors,
        teams=Team.query.join(Tournament, Team.tournament_id == Tournament.id).order_by(Team.name.asc()).all(),
        submit_label="Register player",
    ), 400 if errors else 200


@main_bp.route("/players/<int:player_id>/edit", methods=["GET", "POST"])
def edit_player(player_id):
    """Edit player details and persist changes."""

    player = db.get_or_404(Player, player_id)
    form_data = _player_form_data(player) if request.method == "GET" else _player_form_data()
    errors = {}
    if request.method == "POST":
        errors, cleaned_data = _validate_player_form(form_data, current_player=player)
        if not errors:
            for field, value in cleaned_data.items():
                setattr(player, field, value)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["jersey_number"] = "That jersey number is already used by this team."
            except SQLAlchemyError:
                db.session.rollback()
                errors["form"] = "The player could not be updated. Please try again."
            else:
                flash(f"{player.name} was updated successfully.", "success")
                return redirect(url_for("main.player_detail", player_id=player.id))

    return render_template(
        "player_form.html",
        title="Edit Player",
        heading="Edit player",
        eyebrow="Player management",
        form_data=form_data,
        errors=errors,
        teams=Team.query.join(Tournament, Team.tournament_id == Tournament.id).order_by(Team.name.asc()).all(),
        submit_label="Save changes",
        player=player,
    ), 400 if errors else 200


@main_bp.post("/players/<int:player_id>/delete")
def delete_player(player_id):
    """Delete one player transactionally."""

    player = db.get_or_404(Player, player_id)
    player_name = player.name
    try:
        db.session.delete(player)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("The player could not be deleted. No changes were made.", "error")
        return redirect(url_for("main.player_detail", player_id=player_id))

    flash(f"{player_name} was deleted.", "success")
    return redirect(url_for("main.players"))


@main_bp.get("/players/<int:player_id>")
def player_detail(player_id):
    """Show one player's profile and associated team."""

    player = db.get_or_404(Player, player_id)
    return render_template("player_detail.html", title=player.name, player=player)


@main_bp.get("/matches")
def matches():
    """Show tournament selection, fixture eligibility, and any generated bracket."""

    tournament_id_value = request.args.get("tournament_id", "").strip()
    selected_tournament = None
    if tournament_id_value:
        try:
            selected_tournament = db.session.get(Tournament, int(tournament_id_value))
        except ValueError:
            selected_tournament = None

    generated_matches = []
    bracket_rounds = []
    if selected_tournament:
        generated_matches = sorted(
            selected_tournament.matches,
            key=lambda match: (match.round_number, match.match_number),
        )
        grouped_rounds = {}
        for match in generated_matches:
            grouped_rounds.setdefault(match.round_number, []).append(match)
        bracket_rounds = [
            {"name": round_matches[0].round_name, "matches": round_matches}
            for round_matches in grouped_rounds.values()
        ]

    return render_template(
        "matches.html",
        title="Match Fixtures",
        tournaments=Tournament.query.order_by(Tournament.name.asc()).all(),
        selected_tournament=selected_tournament,
        team_count=len(selected_tournament.teams) if selected_tournament else 0,
        fixture_exists=bool(generated_matches),
        matches=generated_matches,
        bracket_rounds=bracket_rounds,
        status_labels=MATCH_STATUS_LABELS,
    )


@main_bp.post("/matches/generate")
def generate_matches():
    """Generate and persist a tournament bracket exactly once."""

    tournament_id_value = request.form.get("tournament_id", "").strip()
    try:
        tournament_id = int(tournament_id_value)
    except (TypeError, ValueError):
        flash("Select a tournament before generating fixtures.", "error")
        return redirect(url_for("main.matches"))

    tournament = db.get_or_404(Tournament, tournament_id)
    if tournament.matches:
        flash("This tournament already has generated fixtures. Generation is locked.", "error")
        return redirect(url_for("main.matches", tournament_id=tournament.id))

    teams = list(tournament.teams)
    if len(teams) < 2:
        flash("At least 2 registered teams are required to generate fixtures.", "error")
        return redirect(url_for("main.matches", tournament_id=tournament.id))
    if len(teams) > MAX_TEAMS:
        flash(f"A tournament can have at most {MAX_TEAMS} teams.", "error")
        return redirect(url_for("main.matches", tournament_id=tournament.id))

    try:
        generate_knockout_bracket(tournament, teams)
        db.session.commit()
    except (ValueError, SQLAlchemyError):
        db.session.rollback()
        flash("Fixtures could not be generated. No changes were made.", "error")
        return redirect(url_for("main.matches", tournament_id=tournament.id))

    flash(f"Fixtures generated for {tournament.name}.", "success")
    return redirect(url_for("main.matches", tournament_id=tournament.id))


@main_bp.get("/matches/<int:match_id>")
def match_detail(match_id):
    """Show one match, its result, and any available result actions."""

    match = db.get_or_404(Match, match_id)
    return render_template(
        "match_detail.html",
        title=f"Match {match.match_number}",
        match=match,
        status_labels=MATCH_STATUS_LABELS,
    )


@main_bp.post("/matches/<int:match_id>/start")
def start_match(match_id):
    """Move an eligible match into the in-progress state."""

    match = db.get_or_404(Match, match_id)
    try:
        set_match_in_progress(match)
        db.session.commit()
    except (ResultValidationError, SQLAlchemyError) as error:
        db.session.rollback()
        flash(str(error) if isinstance(error, ResultValidationError) else "The match could not be started.", "error")
    else:
        flash("Match marked In Progress.", "success")
    return redirect(url_for("main.match_detail", match_id=match.id))


@main_bp.post("/matches/<int:match_id>/result")
def save_match_result(match_id):
    """Save scores, determine a winner, or hold a tie for manual resolution."""

    match = db.get_or_404(Match, match_id)
    try:
        home_score = parse_score(request.form.get("home_score"), "Team 1")
        away_score = parse_score(request.form.get("away_score"), "Team 2")
        if home_score == away_score:
            save_tied_result(match, home_score, away_score)
            db.session.commit()
            flash("The match is tied. Select the winner after the tiebreaker.", "error")
        else:
            complete_match(match, home_score, away_score)
            db.session.commit()
            flash(f"{match.winner.name} won and advanced.", "success")
    except (ResultValidationError, SQLAlchemyError) as error:
        db.session.rollback()
        flash(str(error) if isinstance(error, ResultValidationError) else "The result could not be saved. No changes were made.", "error")
    return redirect(url_for("main.match_detail", match_id=match.id))


@main_bp.post("/matches/<int:match_id>/resolve-tie")
def resolve_match_tie(match_id):
    """Confirm a manually selected winner for a tied match."""

    match = db.get_or_404(Match, match_id)
    try:
        winner_id = int(request.form.get("winner_id", ""))
        if match.home_score is None or match.away_score is None:
            raise ResultValidationError("Enter and save tied scores before selecting a tiebreaker winner.")
        complete_match(
            match,
            match.home_score,
            match.away_score,
            winner_id=winner_id,
            by_tiebreaker=True,
        )
        db.session.commit()
    except (ResultValidationError, SQLAlchemyError) as error:
        db.session.rollback()
        flash(str(error) if isinstance(error, ResultValidationError) else "The tie resolution could not be saved. No changes were made.", "error")
    except (TypeError, ValueError):
        db.session.rollback()
        flash("Select a valid participating winner.", "error")
    else:
        flash(f"{match.winner.name} won after the tiebreaker and advanced.", "success")
    return redirect(url_for("main.match_detail", match_id=match.id))


@main_bp.get("/settings")
def settings():
    """Placeholder for application settings."""

    return _placeholder_page("Settings", "Application settings will be introduced in a later module.")


def _form_data():
    """Return normalized tournament form values for rendering and validation."""

    return {
        "name": request.form.get("name", "").strip(),
        "sport": request.form.get("sport", "").strip(),
        "venue": request.form.get("venue", "").strip(),
        "tournament_date": request.form.get("tournament_date", "").strip(),
        "description": request.form.get("description", "").strip(),
        "status": request.form.get("status", "").strip().lower(),
    }


def _tournament_form_data(tournament):
    """Convert a tournament model into form values."""

    return {
        "name": tournament.name or "",
        "sport": tournament.sport or "",
        "venue": tournament.venue or "",
        "tournament_date": tournament.tournament_date.isoformat()
        if tournament.tournament_date
        else "",
        "description": tournament.description or "",
        "status": tournament.status or "upcoming",
    }


def _validate_tournament_form(form_data):
    """Validate required tournament fields and convert the date."""

    errors = {}
    if not form_data["name"]:
        errors["name"] = "Tournament name is required."
    if form_data["sport"] not in SPORTS:
        errors["sport"] = "Select a valid sport."
    if not form_data["venue"]:
        errors["venue"] = "Venue is required."
    if not form_data["tournament_date"]:
        errors["tournament_date"] = "Tournament date is required."
    else:
        try:
            form_data["tournament_date"] = datetime.strptime(
                form_data["tournament_date"], "%Y-%m-%d"
            ).date()
        except ValueError:
            errors["tournament_date"] = "Enter a valid tournament date."
    if form_data["status"] not in STATUSES:
        errors["status"] = "Select a valid tournament status."

    return errors, {
        "name": form_data["name"],
        "sport": form_data["sport"],
        "venue": form_data["venue"],
        "tournament_date": form_data["tournament_date"]
        if isinstance(form_data["tournament_date"], date)
        else None,
        "description": form_data["description"],
        "status": form_data["status"],
    }


def _team_form_data(team=None):
    """Return normalized team form values."""

    if team is not None:
        return {
            "name": team.name or "",
            "captain_name": team.captain_name or "",
            "logo_url": team.logo_url or "",
            "tournament_id": str(team.tournament_id),
        }
    return {
        "name": request.form.get("name", "").strip(),
        "captain_name": request.form.get("captain_name", "").strip(),
        "logo_url": request.form.get("logo_url", "").strip(),
        "tournament_id": request.form.get("tournament_id", "").strip(),
    }


def _validate_team_form(form_data, current_team=None):
    """Validate team fields and enforce name uniqueness within a tournament."""

    errors = {}
    if not form_data["name"]:
        errors["name"] = "Team name is required."
    if not form_data["captain_name"]:
        errors["captain_name"] = "Captain name is required."
    try:
        tournament_id = int(form_data["tournament_id"])
    except (TypeError, ValueError):
        tournament_id = None
        errors["tournament_id"] = "Select an existing tournament."
    if tournament_id is not None and db.session.get(Tournament, tournament_id) is None:
        errors["tournament_id"] = "Select an existing tournament."

    if tournament_id is not None and form_data["name"]:
        duplicate_query = Team.query.filter(
            Team.tournament_id == tournament_id,
            func.lower(Team.name) == form_data["name"].lower(),
        )
        if current_team is not None:
            duplicate_query = duplicate_query.filter(Team.id != current_team.id)
        if duplicate_query.first() is not None:
            errors["name"] = "A team with this name already exists in the selected tournament."

    if form_data["logo_url"] and len(form_data["logo_url"]) > 500:
        errors["logo_url"] = "Logo URL must be 500 characters or fewer."
    if form_data["logo_url"] and not _is_safe_external_url(form_data["logo_url"]):
        errors["logo_url"] = "Logo URL must use a valid http or https address."

    return errors, {
        "name": form_data["name"],
        "captain_name": form_data["captain_name"],
        "logo_url": form_data["logo_url"] or None,
        "tournament_id": tournament_id,
    }


def _is_safe_external_url(value):
    """Allow only absolute HTTP(S) URLs for externally hosted team logos."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _player_form_data(player=None):
    """Return normalized player form values."""

    if player is not None:
        return {
            "name": player.name or "",
            "jersey_number": str(player.jersey_number) if player.jersey_number is not None else "",
            "position": player.position or "",
            "team_id": str(player.team_id),
        }
    return {
        "name": request.form.get("name", "").strip(),
        "jersey_number": request.form.get("jersey_number", "").strip(),
        "position": request.form.get("position", "").strip(),
        "team_id": request.form.get("team_id", "").strip(),
    }


def _validate_player_form(form_data, current_player=None):
    """Validate player fields and enforce jersey uniqueness within a team."""

    errors = {}
    if not form_data["name"]:
        errors["name"] = "Player name is required."
    try:
        team_id = int(form_data["team_id"])
    except (TypeError, ValueError):
        team_id = None
        errors["team_id"] = "Select an existing team."
    if team_id is not None and db.session.get(Team, team_id) is None:
        errors["team_id"] = "Select an existing team."

    jersey_number = None
    if form_data["jersey_number"]:
        try:
            jersey_number = int(form_data["jersey_number"])
            if jersey_number < 0:
                raise ValueError
        except ValueError:
            errors["jersey_number"] = "Jersey number must be a whole number of 0 or greater."

    if team_id is not None and jersey_number is not None:
        duplicate_query = Player.query.filter(
            Player.team_id == team_id,
            Player.jersey_number == jersey_number,
        )
        if current_player is not None:
            duplicate_query = duplicate_query.filter(Player.id != current_player.id)
        if duplicate_query.first() is not None:
            errors["jersey_number"] = "That jersey number is already used by this team."

    return errors, {
        "name": form_data["name"],
        "jersey_number": jersey_number,
        "position": form_data["position"] or None,
        "team_id": team_id,
    }


def _placeholder_page(title, description):
    """Render a clear placeholder instead of presenting fake functionality."""

    return render_template(
        "placeholder.html",
        title=title,
        eyebrow="Module 2 foundation",
        heading=title,
        description=description,
        back_url="/",
        back_label="Back to dashboard",
    )
