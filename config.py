"""Application configuration."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration shared by development and testing."""

    SECRET_KEY = "dev-secret-key-change-me"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'tournament.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
