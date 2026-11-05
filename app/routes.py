"""Web routes for the tournament application."""

from flask import Blueprint, render_template
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import Team, Tournament


main_bp = Blueprint("main", __name__)


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


@main_bp.get("/tournaments")
def tournaments():
    """Show actual tournaments from the database."""

    tournament_list = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template(
        "tournaments.html", title="Tournaments", tournaments=tournament_list
    )


@main_bp.get("/tournaments/new")
def new_tournament():
    """Placeholder for the future tournament creation workflow."""

    return render_template(
        "placeholder.html",
        title="Create Tournament",
        eyebrow="Tournament workspace",
        heading="Create Tournament",
        description="Tournament creation will be introduced in a later module.",
        back_url="/tournaments",
        back_label="View tournaments",
    )


@main_bp.get("/tournaments/<int:tournament_id>")
def tournament_detail(tournament_id):
    """Show a read-only view of one tournament."""

    tournament = Tournament.query.get_or_404(tournament_id)
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
