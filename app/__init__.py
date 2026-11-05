"""Application package and factory."""

import click
from flask import Flask

from config import Config
from .extensions import db


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

    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""

        db.create_all()
        click.echo("Initialized the database.")

    return app
