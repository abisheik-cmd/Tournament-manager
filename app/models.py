"""Database models for tournament management."""

from datetime import datetime, timezone

from .extensions import db


class Tournament(db.Model):
    """A competition that contains teams and knockout matches."""

    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sport = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teams = db.relationship(
        "Team", back_populates="tournament", cascade="all, delete-orphan"
    )
    matches = db.relationship(
        "Match", back_populates="tournament", cascade="all, delete-orphan"
    )


class Team(db.Model):
    """A team registered in a tournament."""

    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )

    tournament = db.relationship("Tournament", back_populates="teams")
    players = db.relationship(
        "Player", back_populates="team", cascade="all, delete-orphan"
    )
    home_matches = db.relationship(
        "Match",
        foreign_keys="Match.home_team_id",
        back_populates="home_team",
    )
    away_matches = db.relationship(
        "Match",
        foreign_keys="Match.away_team_id",
        back_populates="away_team",
    )


class Player(db.Model):
    """A player belonging to a team."""

    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    jersey_number = db.Column(db.Integer, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    team = db.relationship("Team", back_populates="players")


class Match(db.Model):
    """A knockout match between two teams."""

    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    round_name = db.Column(db.String(80), nullable=False, default="Round 1")
    scheduled_at = db.Column(db.DateTime, nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    winner_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)

    tournament = db.relationship("Tournament", back_populates="matches")
    home_team = db.relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team = db.relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches"
    )
    winner = db.relationship("Team", foreign_keys=[winner_id])
