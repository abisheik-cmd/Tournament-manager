"""Web routes for the tournament application."""

from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import Team, Tournament


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
    if request.method == "GET":
        form_data = _tournament_form_data(tournament)
    else:
        form_data = _form_data()

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


@main_bp.get("/teams")
def teams():
    """Placeholder for team management."""

    return _placeholder_page("Teams", "Team management will be introduced in a later module.")


@main_bp.get("/players")
def players():
    """Placeholder for player management."""

    return _placeholder_page("Players", "Player management will be introduced in a later module.")


@main_bp.get("/matches")
def matches():
    """Placeholder for match fixtures."""

    return _placeholder_page(
        "Match Fixtures", "Fixture generation and bracket management are coming soon."
    )


@main_bp.get("/settings")
def settings():
    """Placeholder for application settings."""

    return _placeholder_page("Settings", "Application settings will be introduced in a later module.")


def _form_data():
    """Return normalized form values for rendering and validation."""

    return {
        "name": request.form.get("name", "").strip(),
        "sport": request.form.get("sport", "").strip(),
        "venue": request.form.get("venue", "").strip(),
        "tournament_date": request.form.get("tournament_date", "").strip(),
        "description": request.form.get("description", "").strip(),
        "status": request.form.get("status", "").strip().lower(),
    }


def _tournament_form_data(tournament):
    """Convert a model into the values expected by the HTML form."""

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
    """Validate required fields and convert the date to a Python date."""

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
            tournament_date = datetime.strptime(
                form_data["tournament_date"], "%Y-%m-%d"
            ).date()
            form_data["tournament_date"] = tournament_date
        except ValueError:
            errors["tournament_date"] = "Enter a valid tournament date."
    if form_data["status"] not in STATUSES:
        errors["status"] = "Select a valid tournament status."

    cleaned_data = {
        "name": form_data["name"],
        "sport": form_data["sport"],
        "venue": form_data["venue"],
        "tournament_date": form_data["tournament_date"]
        if isinstance(form_data["tournament_date"], date)
        else None,
        "description": form_data["description"],
        "status": form_data["status"],
    }
    return errors, cleaned_data


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
