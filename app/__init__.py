"""Application package and factory."""

import click
from flask import Flask, render_template
from sqlalchemy import inspect, text

from config import Config
from .extensions import db


def _ensure_schema_compatibility():
    """Apply small additive upgrades to an existing database."""

    inspector = inspect(db.engine)
    is_sqlite = db.engine.dialect.name == "sqlite"
    tournament_columns = {
        column["name"] for column in inspector.get_columns("tournaments")
    }
    additions = {
        "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
        "venue": "VARCHAR(160)",
        "tournament_date": "DATE",
        "description": "TEXT",
        "champion_id": "INTEGER",
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

    match_columns = {column["name"] for column in inspector.get_columns("matches")}
    boolean_default = "0" if is_sqlite else "FALSE"
    match_additions = {
        "round_number": "INTEGER NOT NULL DEFAULT 1",
        "match_number": "INTEGER NOT NULL DEFAULT 1",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'scheduled'",
        "is_bye": f"BOOLEAN NOT NULL DEFAULT {boolean_default}",
        "next_match_id": "INTEGER",
        "decided_by_tiebreaker": f"BOOLEAN NOT NULL DEFAULT {boolean_default}",
    }
    with db.engine.begin() as connection:
        for name, definition in match_additions.items():
            if name not in match_columns:
                connection.execute(
                    text(f"ALTER TABLE matches ADD COLUMN {name} {definition}")
                )
        bye_condition = "is_bye = 1" if is_sqlite else "is_bye IS TRUE"
        connection.execute(
            text(
                "UPDATE matches SET status = 'completed' "
                f"WHERE {bye_condition} AND winner_id IS NOT NULL AND status = 'bye'"
            )
        )


def create_app(config_class=Config):
    """Create and configure a Flask application instance."""

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from . import models  # noqa: F401  # Register models before create_all.
    from .routes import main_bp

    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found_error(_error):
        return render_template(
            "error.html",
            title="Page not found",
            status_code=404,
            heading="Page not found",
            message="The page or record you requested could not be found.",
        ), 404

    @app.errorhandler(405)
    def method_not_allowed_error(_error):
        return render_template(
            "error.html",
            title="Method not allowed",
            status_code=405,
            heading="Method not allowed",
            message="This action is not available using that HTTP method.",
        ), 405

    @app.errorhandler(500)
    def internal_server_error(_error):
        db.session.rollback()
        return render_template(
            "error.html",
            title="Something went wrong",
            status_code=500,
            heading="Something went wrong",
            message="The request could not be completed. No changes were saved.",
        ), 500

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
