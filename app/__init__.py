"""Application package and factory."""

import click
from flask import Flask
from sqlalchemy import inspect, text

from config import Config
from .extensions import db


def _ensure_schema_compatibility():
    """Apply small additive upgrades to an existing SQLite database."""

    inspector = inspect(db.engine)
    tournament_columns = {column["name"] for column in inspector.get_columns("tournaments")}
    if "status" not in tournament_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE tournaments "
                    "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"
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
