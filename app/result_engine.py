"""Transactional match result and knockout progression services."""

from .extensions import db
from .models import Match


class ResultValidationError(ValueError):
    """Raised when a match result cannot be accepted safely."""


def parse_score(raw_value, label):
    """Parse a non-negative integer score from form input."""

    value = "" if raw_value is None else str(raw_value).strip()
    if not value:
        raise ResultValidationError(f"{label} score is required.")
    try:
        score = int(value)
    except (TypeError, ValueError) as error:
        raise ResultValidationError(f"{label} score must be a whole number.") from error
    if score < 0:
        raise ResultValidationError(f"{label} score cannot be negative.")
    return score


def validate_participating_match(match):
    """Ensure the match has two distinct teams and accepts a result."""

    if match.is_bye:
        raise ResultValidationError("BYE matches are completed automatically and cannot receive scores.")
    if not match.home_team_id or not match.away_team_id:
        raise ResultValidationError("This match is waiting for both participating teams.")
    if match.home_team_id == match.away_team_id:
        raise ResultValidationError("A team cannot play itself.")
    if match.status == "completed" or match.winner_id:
        raise ResultValidationError(
            "This match is already completed. Result corrections are blocked to protect downstream fixtures."
        )


def set_match_in_progress(match):
    """Mark a match in progress only when both teams are available."""

    validate_participating_match(match)
    if match.status not in {"scheduled", "ready", "in_progress"}:
        raise ResultValidationError("This match is not available to start.")
    match.status = "in_progress"


def _next_slot(match):
    """Return the downstream match and the correct home/away slot."""

    if match.next_match is None:
        return None, None
    slot = "home_team_id" if match.match_number % 2 == 1 else "away_team_id"
    return match.next_match, slot


def advance_winner(match):
    """Insert a completed winner into its downstream match exactly once."""

    if not match.winner_id:
        raise ResultValidationError("A winner must be confirmed before the match can advance.")
    if match.winner_id not in {match.home_team_id, match.away_team_id}:
        raise ResultValidationError("The winner must be one of the participating teams.")

    next_match, slot = _next_slot(match)
    if next_match is None:
        match.tournament.champion_id = match.winner_id
        match.tournament.status = "completed"
        return

    other_slot = "away_team_id" if slot == "home_team_id" else "home_team_id"
    existing_team_id = getattr(next_match, slot)
    other_team_id = getattr(next_match, other_slot)
    if other_team_id == match.winner_id:
        raise ResultValidationError("This team is already assigned to the other slot in the next match.")
    if existing_team_id is None:
        setattr(next_match, slot, match.winner_id)
    elif existing_team_id != match.winner_id:
        raise ResultValidationError("The next match slot is already occupied by another team.")

    if next_match.status not in {"completed", "in_progress"}:
        next_match.status = (
            "ready"
            if next_match.home_team_id and next_match.away_team_id
            else "scheduled"
        )


def complete_match(match, home_score, away_score, winner_id=None, by_tiebreaker=False):
    """Complete a match and advance its confirmed winner transactionally."""

    validate_participating_match(match)
    if home_score is None or away_score is None:
        raise ResultValidationError("Both scores are required.")
    if home_score < 0 or away_score < 0:
        raise ResultValidationError("Scores cannot be negative.")
    if home_score == away_score and winner_id is None:
        raise ResultValidationError("The tied match requires a manual tiebreaker winner.")

    expected_winner_id = (
        match.home_team_id
        if home_score > away_score
        else match.away_team_id
        if away_score > home_score
        else winner_id
    )
    if expected_winner_id not in {match.home_team_id, match.away_team_id}:
        raise ResultValidationError("The selected winner must be one of the participating teams.")
    if home_score != away_score and winner_id is not None and winner_id != expected_winner_id:
        raise ResultValidationError("The selected winner does not have the higher score.")

    match.home_score = home_score
    match.away_score = away_score
    match.winner_id = expected_winner_id
    match.decided_by_tiebreaker = bool(by_tiebreaker)
    match.status = "completed"
    advance_winner(match)
    return match


def save_tied_result(match, home_score, away_score):
    """Persist tied scores without selecting a winner or advancing the bracket."""

    validate_participating_match(match)
    if home_score != away_score:
        raise ResultValidationError("Tie resolution is only available when both scores are equal.")
    match.home_score = home_score
    match.away_score = away_score
    match.winner_id = None
    match.decided_by_tiebreaker = False
    match.status = "in_progress"
    return match
