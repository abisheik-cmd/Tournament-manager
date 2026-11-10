"""Application configuration."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _is_production_environment():
    """Return whether the app is running in a hosted production environment."""
    return bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("ENV") == "production"
    )


def _secret_key():
    """Require an explicit secret in hosted environments, but stay easy locally."""
    secret_key = os.environ.get("SECRET_KEY")
    if secret_key:
        return secret_key
    if _is_production_environment():
        raise RuntimeError(
            "SECRET_KEY must be set in hosted production environments."
        )
    return "dev-only-secret-key-change-me"


def normalize_database_url(database_url):
    """Normalize common hosted PostgreSQL URLs for SQLAlchemy and psycopg."""
    if not database_url:
        return database_url
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    return database_url


def _database_url():
    """Use hosted PostgreSQL when configured and local SQLite otherwise."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        normalized_url = normalize_database_url(database_url)
        if _is_production_environment() and normalized_url.startswith("sqlite"):
            raise RuntimeError(
                "Hosted production deployments require PostgreSQL, not SQLite."
            )
        return normalized_url
    if _is_production_environment():
        raise RuntimeError(
            "DATABASE_URL must point to a managed PostgreSQL database in production."
        )
    return f"sqlite:///{BASE_DIR / 'instance' / 'tournament.db'}"


class Config:
    """Base configuration shared by development and testing."""

    SECRET_KEY = _secret_key()
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
