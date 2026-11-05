from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Match, Player, Team, Tournament


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def test_home_route_and_database_models():
    app = create_app(TestConfig)

    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Tournament Matchup Generator" in response.data

    with app.app_context():
        tournament = Tournament(name="Spring Cup", sport="Football")
        team = Team(name="North Stars", tournament=tournament)
        player = Player(name="Alex Morgan", team=team, jersey_number=10)
        match = Match(
            tournament=tournament,
            home_team=team,
            round_name="Quarterfinal",
        )
        db.session.add(tournament)
        db.session.commit()

        assert tournament.id is not None
        assert team.tournament_id == tournament.id
        assert player.team_id == team.id
        assert match.tournament_id == tournament.id
        assert tournament.teams == [team]
        assert team.players == [player]


def test_database_file_location_is_project_instance_directory():
    app = create_app()
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    assert database_uri.startswith("sqlite:///")
    assert Path(database_uri.removeprefix("sqlite:///" )).parent.name == "instance"
