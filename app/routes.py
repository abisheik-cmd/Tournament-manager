"""Web routes for the tournament application."""

from flask import Blueprint, render_template


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    """Render the foundation home page."""

    return render_template("index.html", title="Tournament Matchup Generator")
