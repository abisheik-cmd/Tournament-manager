"""Application package and factory."""

import click
from flask import Flask
from sqlalchemy import inspect, text

from config import Config
from .extensions import db


def _ensure_schema_compatibility():
    """Apply small additive upgrades to an existing SQLite database."""

    inspector = inspect(db.engine)
    tournament_columns = {
        column["name"] for column in inspector.get_columns("tournaments")
    }
    additions = {
        "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
        "venue": "VARCHAR(160)",
        "tournament_date": "DATE",
        "description": "TEXT",
    }
    missing_columns = [
        (name, definition)
        for name, definition in additions.items()
        if name not in tournament_columns
    ]
    if missing_columns:
        with db.engine.begin() as connection:
            for name, definition in missing_columns:
                connection.execute(
                    text(f"ALTER TABLE tournaments ADD COLUMN {name} {definition}")
                )

    team_columns = {column["name"] for column in inspector.get_columns("teams")}
    player_columns = {column["name"] for column in inspector.get_columns("players")}
    team_additions = {"captain_name": "VARCHAR(120)", "logo_url": "VARCHAR(500)"}
    player_additions = {"position": "VARCHAR(80)"}
    with db.engine.begin() as connection:
        for name, definition in team_additions.items():
            if name not in team_columns:
                connection.execute(
                    text(f"ALTER TABLE teams ADD COLUMN {name} {definition}")
                )
        for name, definition in player_additions.items():
            if name not in player_columns:
                connection.execute(
                    text(f"ALTER TABLE players ADD COLUMN {name} {definition}")
                )


def create_app(config_class=Config):
    """Create and configure a Flask application instance."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from . import models  # noqa: F401  # Register models before create_all.
    from .routes import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        _ensure_schema_compatibility()

    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables and apply safe additive upgrades."""

        db.create_all()
        _ensure_schema_compatibility()
        click.echo("Initialized the database.")

    return app
