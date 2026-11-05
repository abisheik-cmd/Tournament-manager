"""Database models for tournament management."""

from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint

from .extensions import db


class Tournament(db.Model):
    """A competition that contains teams and knockout matches."""

    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sport = db.Column(db.String(80), nullable=False)
    venue = db.Column(db.String(160), nullable=True)
    tournament_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    champion_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teams = db.relationship(
        "Team",
        back_populates="tournament",
        cascade="all, delete-orphan",
        foreign_keys="Team.tournament_id",
    )
    matches = db.relationship(
        "Match", back_populates="tournament", cascade="all, delete-orphan"
    )
    champion = db.relationship("Team", foreign_keys=[champion_id])


class Team(db.Model):
    """A team registered in a tournament."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tournament_id", "name", name="uq_team_name_tournament"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    captain_name = db.Column(db.String(120), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )

    tournament = db.relationship(
        "Tournament", back_populates="teams", foreign_keys=[tournament_id]
    )
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
    __table_args__ = (
        UniqueConstraint("team_id", "jersey_number", name="uq_jersey_number_team"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    jersey_number = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(80), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    team = db.relationship("Team", back_populates="players")


class Match(db.Model):
    """A knockout match or BYE slot in a tournament bracket."""

    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    round_name = db.Column(db.String(80), nullable=False, default="Round 1")
    round_number = db.Column(db.Integer, nullable=False, default=1)
    match_number = db.Column(db.Integer, nullable=False, default=1)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    is_bye = db.Column(db.Boolean, nullable=False, default=False)
    decided_by_tiebreaker = db.Column(db.Boolean, nullable=False, default=False)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    winner_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    next_match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=True)

    tournament = db.relationship("Tournament", back_populates="matches")
    home_team = db.relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team = db.relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches"
    )
    winner = db.relationship("Team", foreign_keys=[winner_id])
    next_match = db.relationship(
        "Match",
        remote_side=[id],
        foreign_keys=[next_match_id],
        backref="previous_matches",
    )
