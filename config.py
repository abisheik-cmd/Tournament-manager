"""Application configuration."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration shared by development and testing."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'tournament.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
