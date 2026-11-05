from datetime import datetime, timezone
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
        assert b"No tournaments yet" in response.data

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
        assert tournament.status == "active"
        assert team.tournament_id == tournament.id
        assert player.team_id == team.id
        assert match.tournament_id == tournament.id
        assert tournament.teams == [team]
        assert team.players == [player]


def test_dashboard_statistics_update_when_records_are_added():
    app = create_app(TestConfig)

    with app.app_context():
        active = Tournament(
            name="City League",
            sport="Football",
            status="active",
            created_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )
        completed = Tournament(
            name="Summer Cup",
            sport="Basketball",
            status="completed",
            created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
        )
        db.session.add_all(
            [
                active,
                completed,
                Team(name="North Stars", tournament=active),
                Team(name="South Stars", tournament=active),
                Team(name="Court Kings", tournament=completed),
            ]
        )
        db.session.commit()

    with app.test_client() as client:
        response = client.get("/")
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "City League" in body
        assert "Summer Cup" in body
        assert 'class="stat-value">2</strong>' in body
        assert 'class="stat-value">1</strong>' in body
        assert 'class="stat-value">3</strong>' in body
        assert "Completed" in body


def test_dashboard_navigation_routes_are_functional_placeholders():
    app = create_app(TestConfig)
    routes = "/tournaments", "/tournaments/new", "/teams", "/players", "/matches", "/settings"

    with app.test_client() as client:
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200
            assert b"Coming soon" in response.data or b"Tournaments" in response.data


def test_database_file_location_is_project_instance_directory():
    app = create_app()
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    assert database_uri.startswith("sqlite:///")
    assert Path(database_uri.removeprefix("sqlite:///" )).parent.name == "instance"
