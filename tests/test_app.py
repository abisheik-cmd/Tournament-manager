from datetime import date, datetime, timezone
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Match, Player, Team, Tournament


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
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


def test_create_tournament_persists_and_updates_dashboard():
    app = create_app(TestConfig)
    form = {
        "name": "Autumn Open",
        "sport": "Tennis",
        "venue": "Riverside Courts",
        "tournament_date": "2026-10-18",
        "description": "Open knockout event",
        "status": "upcoming",
    }
    with app.test_client() as client:
        response = client.post("/tournaments/new", data=form)
        assert response.status_code == 302
        tournament_id = response.headers["Location"].rsplit("/", 1)[-1]
        detail = client.get(f"/tournaments/{tournament_id}")
        assert detail.status_code == 200
        assert b"Riverside Courts" in detail.data
        dashboard = client.get("/")
        assert b"Autumn Open" in dashboard.data

    with app.app_context():
        tournament = db.session.get(Tournament, int(tournament_id))
        assert tournament is not None
        assert tournament.tournament_date == date(2026, 10, 18)
        assert tournament.status == "upcoming"


def test_create_tournament_validates_missing_fields_and_invalid_date():
    app = create_app(TestConfig)
    required_fields = {
        "name": "",
        "sport": "",
        "venue": "",
        "tournament_date": "not-a-date",
        "description": "",
        "status": "",
    }
    with app.test_client() as client:
        response = client.post("/tournaments/new", data=required_fields)
        body = response.get_data(as_text=True)
        assert response.status_code == 400
        assert b"Tournament name is required" in response.data
        assert b"Select a valid sport" in response.data
        assert b"Venue is required" in response.data
        assert b"Enter a valid tournament date" in response.data
        assert b"Select a valid tournament status" in response.data
        assert "not-a-date" in body

    with app.app_context():
        assert db.session.query(Tournament).count() == 0


def test_edit_tournament_updates_sqlite_and_details_immediately():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = Tournament(
            name="Old Name",
            sport="Football",
            venue="Old Venue",
            tournament_date=date(2026, 2, 1),
            description="Old description",
            status="upcoming",
        )
        db.session.add(tournament)
        db.session.commit()
        tournament_id = tournament.id

    with app.test_client() as client:
        response = client.post(
            f"/tournaments/{tournament_id}/edit",
            data={
                "name": "Updated Cup",
                "sport": "Cricket",
                "venue": "New Ground",
                "tournament_date": "2026-03-02",
                "description": "Updated description",
                "status": "active",
            },
        )
        assert response.status_code == 302
        detail = client.get(f"/tournaments/{tournament_id}")
        assert b"Updated Cup" in detail.data
        assert b"New Ground" in detail.data
        assert b"Updated description" in detail.data
        assert b"Active" in detail.data

    with app.app_context():
        updated = db.session.get(Tournament, tournament_id)
        assert updated.name == "Updated Cup"
        assert updated.sport == "Cricket"
        assert updated.status == "active"
        assert updated.tournament_date == date(2026, 3, 2)


def test_tournament_listing_search_and_filters():
    app = create_app(TestConfig)
    with app.app_context():
        db.session.add_all(
            [
                Tournament(name="Football Finals", sport="Football", venue="A", status="active"),
                Tournament(name="Cricket Classic", sport="Cricket", venue="B", status="completed"),
                Tournament(name="Football Juniors", sport="Football", venue="C", status="upcoming"),
            ]
        )
        db.session.commit()

    with app.test_client() as client:
        response = client.get("/tournaments?search=final")
        assert b"Football Finals" in response.data
        assert b"Cricket Classic" not in response.data
        response = client.get("/tournaments?sport=Football&status=upcoming")
        assert b"Football Juniors" in response.data
        assert b"Football Finals" not in response.data
        assert b"Clear filters" in response.data
        response = client.get("/tournaments?status=invalid")
        assert b"Football Finals" in response.data
        assert b"Cricket Classic" in response.data


def test_tournament_delete_cascades_associated_records_and_updates_dashboard():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = Tournament(
            name="Delete Cup",
            sport="Basketball",
            venue="Arena",
            tournament_date=date(2026, 4, 4),
            status="active",
        )
        team = Team(name="Delete Team", tournament=tournament)
        Player(name="Delete Player", team=team)
        Match(tournament=tournament, home_team=team, round_name="Final")
        db.session.add(tournament)
        db.session.commit()
        tournament_id, team_id = tournament.id, team.id

    with app.test_client() as client:
        response = client.post(f"/tournaments/{tournament_id}/delete")
        assert response.status_code == 302
        assert client.get(f"/tournaments/{tournament_id}").status_code == 404
        assert b"Delete Cup" not in client.get("/").data

    with app.app_context():
        assert db.session.get(Tournament, tournament_id) is None
        assert db.session.get(Team, team_id) is None
        assert db.session.query(Player).count() == 0
        assert db.session.query(Match).count() == 0


def test_database_persists_after_application_restart(tmp_path):
    database_path = tmp_path / "restart.db"

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app = create_app(FileConfig)
    with app.test_client() as client:
        response = client.post(
            "/tournaments/new",
            data={
                "name": "Persistent Cup",
                "sport": "Volleyball",
                "venue": "Community Hall",
                "tournament_date": "2026-05-05",
                "description": "Persisted record",
                "status": "completed",
            },
        )
        assert response.status_code == 302

    restarted_app = create_app(FileConfig)
    with restarted_app.test_client() as client:
        response = client.get("/tournaments?search=Persistent")
        assert response.status_code == 200
        assert b"Persistent Cup" in response.data


def test_database_file_location_is_project_instance_directory():
    app = create_app()
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    assert database_uri.startswith("sqlite:///")
    assert Path(database_uri.removeprefix("sqlite:///" )).parent.name == "instance"
