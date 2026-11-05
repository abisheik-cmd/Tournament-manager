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
        match = Match(tournament=tournament, home_team=team, round_name="Quarterfinal")
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
        active = Tournament(name="City League", sport="Football", status="active", created_at=datetime(2026, 1, 10, tzinfo=timezone.utc))
        completed = Tournament(name="Summer Cup", sport="Basketball", status="completed", created_at=datetime(2026, 1, 11, tzinfo=timezone.utc))
        db.session.add_all([active, completed, Team(name="North Stars", tournament=active), Team(name="South Stars", tournament=active), Team(name="Court Kings", tournament=completed)])
        db.session.commit()
    with app.test_client() as client:
        response = client.get("/")
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "City League" in body and "Summer Cup" in body
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
            assert b"Coming soon" in response.data or b"Tournaments" in response.data or b"Registered teams" in response.data or b"Registered players" in response.data


def test_create_tournament_persists_and_updates_dashboard():
    app = create_app(TestConfig)
    form = {"name": "Autumn Open", "sport": "Tennis", "venue": "Riverside Courts", "tournament_date": "2026-10-18", "description": "Open knockout event", "status": "upcoming"}
    with app.test_client() as client:
        response = client.post("/tournaments/new", data=form)
        assert response.status_code == 302
        tournament_id = response.headers["Location"].rsplit("/", 1)[-1]
        detail = client.get(f"/tournaments/{tournament_id}")
        assert detail.status_code == 200 and b"Riverside Courts" in detail.data
        assert b"Autumn Open" in client.get("/").data
    with app.app_context():
        tournament = db.session.get(Tournament, int(tournament_id))
        assert tournament is not None and tournament.tournament_date == date(2026, 10, 18)
        assert tournament.status == "upcoming"


def test_create_tournament_validates_missing_fields_and_invalid_date():
    app = create_app(TestConfig)
    required_fields = {"name": "", "sport": "", "venue": "", "tournament_date": "not-a-date", "description": "", "status": ""}
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
        tournament = Tournament(name="Old Name", sport="Football", venue="Old Venue", tournament_date=date(2026, 2, 1), description="Old description", status="upcoming")
        db.session.add(tournament)
        db.session.commit()
        tournament_id = tournament.id
    with app.test_client() as client:
        response = client.post(f"/tournaments/{tournament_id}/edit", data={"name": "Updated Cup", "sport": "Cricket", "venue": "New Ground", "tournament_date": "2026-03-02", "description": "Updated description", "status": "active"})
        assert response.status_code == 302
        detail = client.get(f"/tournaments/{tournament_id}")
        assert b"Updated Cup" in detail.data and b"New Ground" in detail.data and b"Updated description" in detail.data and b"Active" in detail.data
    with app.app_context():
        updated = db.session.get(Tournament, tournament_id)
        assert updated.name == "Updated Cup" and updated.sport == "Cricket" and updated.status == "active" and updated.tournament_date == date(2026, 3, 2)


def test_tournament_listing_search_and_filters():
    app = create_app(TestConfig)
    with app.app_context():
        db.session.add_all([Tournament(name="Football Finals", sport="Football", venue="A", status="active"), Tournament(name="Cricket Classic", sport="Cricket", venue="B", status="completed"), Tournament(name="Football Juniors", sport="Football", venue="C", status="upcoming")])
        db.session.commit()
    with app.test_client() as client:
        response = client.get("/tournaments?search=final")
        assert b"Football Finals" in response.data and b"Cricket Classic" not in response.data
        response = client.get("/tournaments?sport=Football&status=upcoming")
        assert b"Football Juniors" in response.data and b"Football Finals" not in response.data and b"Clear filters" in response.data
        response = client.get("/tournaments?status=invalid")
        assert b"Football Finals" in response.data and b"Cricket Classic" in response.data


def test_tournament_delete_cascades_associated_records_and_updates_dashboard():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = Tournament(name="Delete Cup", sport="Basketball", venue="Arena", tournament_date=date(2026, 4, 4), status="active")
        team = Team(name="Delete Team", tournament=tournament)
        Player(name="Delete Player", team=team)
        Match(tournament=tournament, home_team=team, round_name="Final")
        db.session.add(tournament)
        db.session.commit()
        tournament_id, team_id = tournament.id, team.id
    with app.test_client() as client:
        response = client.post(f"/tournaments/{tournament_id}/delete")
        assert response.status_code == 302 and client.get(f"/tournaments/{tournament_id}").status_code == 404
        assert b"Delete Cup" not in client.get("/").data
    with app.app_context():
        assert db.session.get(Tournament, tournament_id) is None and db.session.get(Team, team_id) is None
        assert db.session.query(Player).count() == 0 and db.session.query(Match).count() == 0


def _create_tournament(name="League Cup"):
    tournament = Tournament(name=name, sport="Football", venue="Main Ground", status="active")
    db.session.add(tournament)
    db.session.commit()
    return tournament


def _team_form(name="North Stars", tournament_id="1", captain="Alex Morgan"):
    return {"name": name, "captain_name": captain, "logo_url": "https://example.com/logo.png", "tournament_id": tournament_id}


def _player_form(name="Jordan Lee", team_id="1", jersey="10", position="Forward"):
    return {"name": name, "team_id": team_id, "jersey_number": jersey, "position": position}


def test_team_creation_duplicate_scope_and_relationship():
    app = create_app(TestConfig)
    with app.app_context():
        first_tournament = _create_tournament("League Cup")
        second_tournament = _create_tournament("Regional Cup")
        first_id, second_id = first_tournament.id, second_tournament.id
    with app.test_client() as client:
        response = client.post("/teams/new", data=_team_form(tournament_id=str(first_id)))
        assert response.status_code == 302
        duplicate = client.post("/teams/new", data=_team_form(tournament_id=str(first_id)))
        assert duplicate.status_code == 400
        assert b"already exists" in duplicate.data
        allowed_other_tournament = client.post("/teams/new", data=_team_form(tournament_id=str(second_id)))
        assert allowed_other_tournament.status_code == 302
    with app.app_context():
        assert db.session.query(Team).count() == 2
        assert db.session.get(Tournament, first_id).teams[0].name == "North Stars"


def test_team_validation_and_editing():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = _create_tournament()
        tournament_id = tournament.id
    with app.test_client() as client:
        invalid = client.post("/teams/new", data=_team_form(name="", tournament_id="999", captain=""))
        assert invalid.status_code == 400
        assert b"Team name is required" in invalid.data and b"Captain name is required" in invalid.data
        team_response = client.post("/teams/new", data=_team_form(tournament_id=str(tournament_id)))
        team_id = int(team_response.headers["Location"].rsplit("/", 1)[-1])
        edited = client.post(f"/teams/{team_id}/edit", data=_team_form(name="Updated Stars", tournament_id=str(tournament_id), captain="New Captain"))
        assert edited.status_code == 302
        assert b"Updated Stars" in client.get(f"/teams/{team_id}").data
    with app.app_context():
        team = db.session.get(Team, team_id)
        assert team.name == "Updated Stars" and team.captain_name == "New Captain"


def test_player_creation_duplicate_jersey_editing_and_relationship():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = _create_tournament()
        team = Team(name="Player Team", captain_name="Captain", tournament=tournament)
        db.session.add(team)
        db.session.commit()
        team_id = team.id
    with app.test_client() as client:
        created = client.post("/players/new", data=_player_form(team_id=str(team_id)))
        assert created.status_code == 302
        player_id = int(created.headers["Location"].rsplit("/", 1)[-1])
        duplicate = client.post("/players/new", data=_player_form(name="Other Player", team_id=str(team_id)))
        assert duplicate.status_code == 400 and b"already used" in duplicate.data
        edited = client.post(f"/players/{player_id}/edit", data=_player_form(name="Updated Player", team_id=str(team_id), jersey="11", position="Captain"))
        assert edited.status_code == 302
        assert b"Updated Player" in client.get(f"/players/{player_id}").data
    with app.app_context():
        player = db.session.get(Player, player_id)
        assert player.name == "Updated Player" and player.jersey_number == 11 and player.position == "Captain"
        assert player.team.name == "Player Team"


def test_player_validation_and_deletion_cascade():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = _create_tournament()
        team = Team(name="Roster Team", captain_name="Captain", tournament=tournament)
        db.session.add(team)
        db.session.commit()
        team_id = team.id
    with app.test_client() as client:
        invalid = client.post("/players/new", data=_player_form(name="", team_id="999", jersey="not-number"))
        assert invalid.status_code == 400
        assert b"Player name is required" in invalid.data and b"Select an existing team" in invalid.data
        created = client.post("/players/new", data=_player_form(team_id=str(team_id)))
        player_id = int(created.headers["Location"].rsplit("/", 1)[-1])
        deleted = client.post(f"/players/{player_id}/delete")
        assert deleted.status_code == 302
        assert client.get(f"/players/{player_id}").status_code == 404
    with app.app_context():
        assert db.session.get(Player, player_id) is None
        assert db.session.get(Team, team_id) is not None


def test_team_deletion_removes_players_and_clears_match_references():
    app = create_app(TestConfig)
    with app.app_context():
        tournament = _create_tournament()
        team = Team(name="Match Team", captain_name="Captain", tournament=tournament)
        opponent = Team(name="Opponent", captain_name="Captain", tournament=tournament)
        player = Player(name="Roster Player", team=team)
        match = Match(tournament=tournament, home_team=team, away_team=opponent, winner=team)
        db.session.add_all([team, opponent, player, match])
        db.session.commit()
        team_id, player_id, match_id = team.id, player.id, match.id
    with app.test_client() as client:
        response = client.post(f"/teams/{team_id}/delete")
        assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Team, team_id) is None and db.session.get(Player, player_id) is None
        remaining_match = db.session.get(Match, match_id)
        assert remaining_match is not None
        assert remaining_match.home_team_id is None and remaining_match.winner_id is None
        assert remaining_match.away_team_id is not None


def test_team_and_player_database_persistence_after_restart(tmp_path):
    database_path = tmp_path / "team-player-restart.db"
    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"
    app = create_app(FileConfig)
    with app.app_context():
        tournament = _create_tournament("Persistent Tournament")
        team = Team(name="Persistent Team", captain_name="Persisted Captain", tournament=tournament)
        db.session.add(team)
        db.session.commit()
        team_id = team.id
    with app.test_client() as client:
        response = client.post("/players/new", data=_player_form(name="Persistent Player", team_id=str(team_id), jersey="7"))
        assert response.status_code == 302
    restarted_app = create_app(FileConfig)
    with restarted_app.test_client() as client:
        assert b"Persistent Team" in client.get("/teams?search=Persistent").data
        assert b"Persistent Player" in client.get("/players?search=Persistent").data


def test_database_file_location_is_project_instance_directory():
    app = create_app()
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    assert database_uri.startswith("sqlite:///")
    assert Path(database_uri.removeprefix("sqlite:///" )).parent.name == "instance"


import random

import pytest

from app.fixture_engine import generate_knockout_bracket, next_power_of_two


def _fixture_tournament(team_count, name="Fixture Cup"):
    tournament = Tournament(
        name=name,
        sport="Football",
        venue="Bracket Arena",
        status="active",
    )
    db.session.add(tournament)
    db.session.flush()
    teams = [
        Team(
            name=f"Fixture Team {index}",
            captain_name=f"Captain {index}",
            tournament=tournament,
        )
        for index in range(team_count)
    ]
    db.session.add_all(teams)
    db.session.flush()
    return tournament, teams


@pytest.mark.parametrize("team_count", [2, 3, 4, 5, 6, 7, 8, 10, 16, 32, 64])
def test_fixture_engine_generates_valid_bracket_for_every_supported_team_count(team_count):
    app = create_app(TestConfig)
    with app.app_context():
        tournament, teams = _fixture_tournament(team_count, name=f"Fixture {team_count}")
        matches = generate_knockout_bracket(
            tournament, teams, rng=random.Random(team_count)
        )
        db.session.commit()
        bracket_size = next_power_of_two(team_count)
        first_round = [match for match in matches if match.round_number == 1]
        max_round = max(match.round_number for match in matches)
        assert len(matches) == bracket_size - 1
        assert len(first_round) == bracket_size // 2
        assert sum(match.is_bye for match in first_round) == bracket_size - team_count
        if bracket_size - team_count >= 2:
            half = len(first_round) // 2
            assert any(match.is_bye for match in first_round[:half])
            assert any(match.is_bye for match in first_round[half:])
        first_round_teams = [
            team_id
            for match in first_round
            for team_id in (match.home_team_id, match.away_team_id)
            if team_id is not None
        ]
        assert sorted(first_round_teams) == sorted(team.id for team in teams)
        assert len(first_round_teams) == len(set(first_round_teams)) == team_count
        assert all(match.home_team_id != match.away_team_id for match in first_round)
        assert all(
            match.next_match_id is not None
            for match in matches
            if match.round_number < max_round
        )
        for match in first_round:
            if match.is_bye:
                assert match.away_team_id is None
                assert match.winner_id == match.home_team_id
                assert match.status == "completed"


def test_fixture_generation_route_requires_eligibility_and_prevents_duplicates():
    app = create_app(TestConfig)
    with app.app_context():
        small_tournament, _ = _fixture_tournament(1, name="Too Small")
        valid_tournament, _ = _fixture_tournament(3, name="Valid Bracket")
        small_id, valid_id = small_tournament.id, valid_tournament.id
        db.session.commit()

    with app.test_client() as client:
        too_small = client.post(
            "/matches/generate",
            data={"tournament_id": str(small_id)},
            follow_redirects=True,
        )
        assert too_small.status_code == 200
        assert b"At least 2 registered teams" in too_small.data
        generated = client.post(
            "/matches/generate",
            data={"tournament_id": str(valid_id)},
            follow_redirects=True,
        )
        assert generated.status_code == 200
        assert b"Generated bracket" in generated.data
        assert b"BYE" in generated.data
        duplicate = client.post(
            "/matches/generate",
            data={"tournament_id": str(valid_id)},
            follow_redirects=True,
        )
        assert duplicate.status_code == 200
        assert b"already has generated fixtures" in duplicate.data

    with app.app_context():
        assert db.session.query(Match).filter_by(tournament_id=valid_id).count() == 3


def test_fixture_generation_persists_after_application_restart(tmp_path):
    database_path = tmp_path / "fixtures-restart.db"

    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

    app = create_app(FileConfig)
    with app.app_context():
        tournament, _ = _fixture_tournament(4, name="Persistent Bracket")
        tournament_id = tournament.id
        db.session.commit()
    with app.test_client() as client:
        response = client.post(
            "/matches/generate", data={"tournament_id": str(tournament_id)}
        )
        assert response.status_code == 302

    restarted_app = create_app(FileConfig)
    with restarted_app.test_client() as client:
        response = client.get(f"/matches?tournament_id={tournament_id}")
        assert response.status_code == 200
        assert b"Generated bracket" in response.data
        assert b"Persistent Bracket" in response.data
    with restarted_app.app_context():
        assert (
            db.session.query(Match)
            .filter_by(tournament_id=tournament_id)
            .count()
            == 3
        )


def test_fixture_engine_rejects_more_than_64_teams():
    app = create_app(TestConfig)
    with app.app_context():
        tournament, teams = _fixture_tournament(65, name="Too Large")
        with pytest.raises(ValueError, match="at most 64"):
            generate_knockout_bracket(tournament, teams)


from app.result_engine import ResultValidationError, complete_match


def _generated_match_app(tmp_path=None, team_count=4):
    config = TestConfig
    if tmp_path is not None:
        class FileConfig(TestConfig):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'module6.db'}"
        config = FileConfig
    app = create_app(config)
    with app.app_context():
        tournament, teams = _fixture_tournament(team_count, name=f"Scoring Cup {team_count}")
        generate_knockout_bracket(tournament, teams, rng=random.Random(41))
        db.session.commit()
        tournament_id = tournament.id
    return app, tournament_id


def _round_matches(tournament, round_number):
    return sorted([match for match in tournament.matches if match.round_number == round_number], key=lambda match: match.match_number)


def test_team_one_and_team_two_score_wins_progress_to_correct_next_slots():
    app, tournament_id = _generated_match_app(team_count=4)
    with app.app_context():
        tournament = db.session.get(Tournament, tournament_id)
        first, second = _round_matches(tournament, 1)
        first_winner_id, second_winner_id = first.home_team_id, second.away_team_id
        first_id, second_id, next_id = first.id, second.id, first.next_match_id
    with app.test_client() as client:
        assert client.post(f"/matches/{first_id}/result", data={"home_score": "3", "away_score": "1"}).status_code == 302
        assert client.post(f"/matches/{second_id}/result", data={"home_score": "0", "away_score": "2"}).status_code == 302
    with app.app_context():
        first_match, second_match, next_match = db.session.get(Match, first_id), db.session.get(Match, second_id), db.session.get(Match, next_id)
        assert first_match.winner_id == first_winner_id and second_match.winner_id == second_winner_id
        first_slot = "home_team_id" if first_match.match_number % 2 else "away_team_id"
        second_slot = "home_team_id" if second_match.match_number % 2 else "away_team_id"
        assert getattr(next_match, first_slot) == first_winner_id and getattr(next_match, second_slot) == second_winner_id
        assert next_match.status == "ready"


def test_negative_invalid_and_missing_scores_are_rejected():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        match_id = _round_matches(db.session.get(Tournament, tournament_id), 1)[0].id
    with app.test_client() as client:
        for scores, message in [({"home_score": "-1", "away_score": "2"}, b"cannot be negative"), ({"home_score": "abc", "away_score": "2"}, b"whole number"), ({"home_score": "", "away_score": "2"}, b"is required")]:
            response = client.post(f"/matches/{match_id}/result", data=scores, follow_redirects=True)
            assert response.status_code == 200 and message in response.data
    with app.app_context():
        match = db.session.get(Match, match_id)
        assert match.home_score is None and match.away_score is None and match.winner_id is None


def test_tie_requires_manual_tiebreaker_and_records_decision():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        match = _round_matches(db.session.get(Tournament, tournament_id), 1)[0]
        match_id, away_id = match.id, match.away_team_id
    with app.test_client() as client:
        tied = client.post(f"/matches/{match_id}/result", data={"home_score": "2", "away_score": "2"}, follow_redirects=True)
        assert tied.status_code == 200 and b"Tie resolution required" in tied.data
        resolved = client.post(f"/matches/{match_id}/resolve-tie", data={"winner_id": str(away_id)}, follow_redirects=True)
        assert resolved.status_code == 200 and b"won after the tiebreaker" in resolved.data
    with app.app_context():
        match = db.session.get(Match, match_id)
        assert match.status == "completed" and match.winner_id == away_id and match.decided_by_tiebreaker is True


def test_bye_is_completed_and_automatically_occupies_next_slot():
    app, tournament_id = _generated_match_app(team_count=3)
    with app.app_context():
        bye = next(match for match in db.session.get(Tournament, tournament_id).matches if match.is_bye)
        assert bye.status == "completed" and bye.winner_id == bye.home_team_id
        assert bye.next_match is not None and bye.winner_id in {bye.next_match.home_team_id, bye.next_match.away_team_id}


def test_match_status_transitions_from_scheduled_to_in_progress_to_completed():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        match_id = _round_matches(db.session.get(Tournament, tournament_id), 1)[0].id
        assert db.session.get(Match, match_id).status == "scheduled"
    with app.test_client() as client:
        assert client.post(f"/matches/{match_id}/start").status_code == 302
        assert client.post(f"/matches/{match_id}/result", data={"home_score": "1", "away_score": "0"}).status_code == 302
    with app.app_context():
        assert db.session.get(Match, match_id).status == "completed"


def test_final_completion_sets_champion_tournament_status_and_dashboard_display():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        match = _round_matches(db.session.get(Tournament, tournament_id), 1)[0]
        match_id, winner_id = match.id, match.home_team_id
    with app.test_client() as client:
        response = client.post(f"/matches/{match_id}/result", data={"home_score": "4", "away_score": "0"}, follow_redirects=True)
        assert response.status_code == 200 and b"Winner confirmed" in response.data
        assert b"Tournament champion" in client.get(f"/tournaments/{tournament_id}").data and b"Champion" in client.get("/").data
    with app.app_context():
        tournament = db.session.get(Tournament, tournament_id)
        assert tournament.status == "completed" and tournament.champion_id == winner_id


def test_result_correction_and_bye_score_entry_are_blocked_safely():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        final_id = _round_matches(db.session.get(Tournament, tournament_id), 1)[0].id
    with app.test_client() as client:
        client.post(f"/matches/{final_id}/result", data={"home_score": "2", "away_score": "1"})
        correction = client.post(f"/matches/{final_id}/result", data={"home_score": "0", "away_score": "9"}, follow_redirects=True)
        assert correction.status_code == 200 and b"Result corrections are blocked" in correction.data
    with app.app_context():
        final = db.session.get(Match, final_id)
        assert final.home_score == 2 and final.away_score == 1
    bye_app, bye_tournament_id = _generated_match_app(team_count=3)
    with bye_app.app_context():
        bye_id = next(match.id for match in db.session.get(Tournament, bye_tournament_id).matches if match.is_bye)
    with bye_app.test_client() as client:
        response = client.post(f"/matches/{bye_id}/result", data={"home_score": "1", "away_score": "0"}, follow_redirects=True)
        assert b"BYE matches" in response.data


def test_duplicate_progression_is_rejected_without_overwriting_next_slot():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        match = _round_matches(db.session.get(Tournament, tournament_id), 1)[0]
        complete_match(match, 3, 1)
        db.session.commit()
        with pytest.raises(ResultValidationError, match="already completed"):
            complete_match(match, 4, 0)
        assert match.home_score == 3 and match.away_score == 1


def test_match_results_persist_after_application_restart(tmp_path):
    app, tournament_id = _generated_match_app(tmp_path=tmp_path, team_count=2)
    with app.app_context():
        match_id = _round_matches(db.session.get(Tournament, tournament_id), 1)[0].id
    with app.test_client() as client:
        client.post(f"/matches/{match_id}/result", data={"home_score": "5", "away_score": "3"})
    class FileConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'module6.db'}"
    restarted_app = create_app(FileConfig)
    with restarted_app.app_context():
        match = db.session.get(Match, match_id)
        assert match.home_score == 5 and match.away_score == 3 and match.status == "completed" and match.tournament.status == "completed"


def test_waiting_match_and_invalid_tiebreaker_winner_are_rejected():
    app, tournament_id = _generated_match_app(team_count=3)
    with app.app_context():
        tournament = db.session.get(Tournament, tournament_id)
        waiting = next(match for match in tournament.matches if match.round_number == 2)
        real_match = next(match for match in _round_matches(tournament, 1) if not match.is_bye)
        outsider = Team(name="Outsider", captain_name="Captain", tournament=tournament)
        db.session.add(outsider)
        db.session.commit()
        waiting_id, real_match_id, outsider_id = waiting.id, real_match.id, outsider.id
    with app.test_client() as client:
        waiting_result = client.post(f"/matches/{waiting_id}/result", data={"home_score": "1", "away_score": "0"}, follow_redirects=True)
        assert b"waiting for both participating teams" in waiting_result.data
        client.post(f"/matches/{real_match_id}/result", data={"home_score": "2", "away_score": "2"})
        invalid_winner = client.post(f"/matches/{real_match_id}/resolve-tie", data={"winner_id": str(outsider_id)}, follow_redirects=True)
        assert b"The selected winner must be one of the participating teams" in invalid_winner.data



def test_fixture_edge_cases_for_zero_one_and_sixty_five_teams():
    app = create_app(TestConfig)
    with app.app_context():
        empty_tournament = _create_tournament("Empty Cup")
        one_team_tournament, _ = _fixture_tournament(1, name="One Team Cup")
        large_tournament, _ = _fixture_tournament(65, name="Oversized Cup")
        empty_id, one_team_id, large_id = empty_tournament.id, one_team_tournament.id, large_tournament.id
        with app.test_client() as client:
            for tournament_id, message in ((empty_id, b"At least 2 registered teams"), (one_team_id, b"At least 2 registered teams"), (large_id, b"at most 64 teams")):
                response = client.post("/matches/generate", data={"tournament_id": str(tournament_id)}, follow_redirects=True)
                assert response.status_code == 200 and message in response.data
        assert db.session.query(Match).count() == 0


def test_deleting_team_after_fixture_generation_clears_all_team_references():
    app = create_app(TestConfig)
    with app.app_context():
        tournament, teams = _fixture_tournament(4, name="Delete After Fixtures")
        tournament_id, deleted_team_id = tournament.id, teams[0].id
        generate_knockout_bracket(tournament, teams, rng=random.Random(8))
        db.session.commit()
    with app.test_client() as client:
        response = client.post(f"/teams/{deleted_team_id}/delete")
        assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Team, deleted_team_id) is None
        matches = db.session.query(Match).filter_by(tournament_id=tournament_id).all()
        assert all(deleted_team_id not in {match.home_team_id, match.away_team_id, match.winner_id} for match in matches)


def test_deleting_completed_tournament_with_champion_preserves_foreign_key_integrity():
    app, tournament_id = _generated_match_app(team_count=2)
    with app.app_context():
        final = _round_matches(db.session.get(Tournament, tournament_id), 1)[0]
        complete_match(final, 2, 0)
        db.session.commit()
    with app.test_client() as client:
        response = client.post(f"/tournaments/{tournament_id}/delete")
        assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Tournament, tournament_id) is None
        assert db.session.query(Team).count() == 0
        assert db.session.query(Match).count() == 0


def test_invalid_methods_missing_records_and_unsafe_logo_urls_are_handled_cleanly():
    app = create_app(TestConfig)
    with app.test_client() as client:
        assert client.post("/").status_code == 405
        assert b"Method not allowed" in client.post("/").data
        assert client.get("/tournaments/999999/delete").status_code == 405
        missing = client.get("/tournaments/999999")
        assert missing.status_code == 404 and b"Page not found" in missing.data
        invalid_logo = client.post("/teams/new", data={"name": "Unsafe", "captain_name": "Captain", "logo_url": "javascript:alert(1)", "tournament_id": "999"})
        assert invalid_logo.status_code == 400
        assert b"valid http or https" in invalid_logo.data


def test_user_supplied_html_is_escaped_and_configuration_is_not_debug_by_default():
    from config import Config

    app = create_app(TestConfig)
    form = {"name": "<script>alert(1)</script>", "sport": "Football", "venue": "Safe Arena", "tournament_date": "2026-11-05", "description": "<b>safe text</b>", "status": "upcoming"}
    with app.test_client() as client:
        response = client.post("/tournaments/new", data=form)
        assert response.status_code == 302
        detail = client.get(response.headers["Location"])
        assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in detail.data
        assert b"<script>alert(1)</script>" not in detail.data
    assert Config.DEBUG is False
