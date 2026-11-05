"""Randomized single-elimination bracket generation."""

import random

from .extensions import db
from .models import Match

MAX_TEAMS = 64


ROUND_NAMES = {
    2: ["Final"],
    4: ["Semi-final", "Final"],
    8: ["Quarter-final", "Semi-final", "Final"],
    16: ["Round of 16", "Quarter-final", "Semi-final", "Final"],
    32: ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"],
    64: [
        "Round of 64",
        "Round of 32",
        "Round of 16",
        "Quarter-final",
        "Semi-final",
        "Final",
    ],
}


def next_power_of_two(team_count):
    """Return the smallest power of two greater than or equal to team_count."""

    bracket_size = 1
    while bracket_size < team_count:
        bracket_size *= 2
    return bracket_size


def round_names(bracket_size):
    """Return meaningful round names for a supported bracket size."""

    if bracket_size in ROUND_NAMES:
        return ROUND_NAMES[bracket_size]
    rounds = bracket_size.bit_length() - 1
    return [f"Round {bracket_size // (2**index)}" for index in range(rounds - 1)] + [
        "Final"
    ]


def distributed_bye_indexes(match_count, bye_count, rng):
    """Choose randomized BYE slots with balanced left/right bracket halves."""

    if bye_count == 0:
        return set()
    half_size = match_count // 2
    left_indexes = list(range(half_size))
    right_indexes = list(range(half_size, match_count))
    rng.shuffle(left_indexes)
    rng.shuffle(right_indexes)
    left_count = bye_count // 2
    right_count = bye_count - left_count
    if bye_count % 2 and rng.choice((True, False)):
        left_count, right_count = right_count, left_count
    return set(left_indexes[:left_count] + right_indexes[:right_count])


def generate_knockout_bracket(tournament, teams, rng=None):
    """Build and stage a complete randomized knockout bracket for a tournament.

    The caller owns the transaction. This function adds and flushes Match objects,
    but does not commit, allowing the route to roll back the whole bracket safely.
    """

    team_list = list(teams)
    team_count = len(team_list)
    if team_count < 2:
        raise ValueError("At least 2 registered teams are required to generate fixtures.")
    if team_count > MAX_TEAMS:
        raise ValueError(f"A tournament can have at most {MAX_TEAMS} teams.")

    randomizer = rng or random
    randomizer.shuffle(team_list)
    bracket_size = next_power_of_two(team_count)
    first_round_match_count = bracket_size // 2
    bye_count = bracket_size - team_count
    bye_match_indexes = distributed_bye_indexes(
        first_round_match_count, bye_count, randomizer
    )
    names = round_names(bracket_size)

    rounds = []
    first_round = []
    team_index = 0
    for match_index in range(first_round_match_count):
        if match_index in bye_match_indexes:
            home_team = team_list[team_index]
            team_index += 1
            away_team = None
            is_bye = True
            status = "bye"
            winner = home_team
        else:
            home_team = team_list[team_index]
            away_team = team_list[team_index + 1]
            team_index += 2
            is_bye = False
            status = "scheduled"
            winner = None

        first_round.append(
            Match(
                tournament=tournament,
                round_name=names[0],
                round_number=1,
                match_number=match_index + 1,
                home_team=home_team,
                away_team=away_team,
                winner=winner,
                status=status,
                is_bye=is_bye,
            )
        )
    rounds.append(first_round)

    round_number = 2
    while len(rounds[-1]) > 1:
        match_count = len(rounds[-1]) // 2
        rounds.append(
            [
                Match(
                    tournament=tournament,
                    round_name=names[round_number - 1],
                    round_number=round_number,
                    match_number=match_index + 1,
                    status="pending",
                )
                for match_index in range(match_count)
            ]
        )
        round_number += 1

    all_matches = [match for bracket_round in rounds for match in bracket_round]
    db.session.add_all(all_matches)
    db.session.flush()

    for round_index, bracket_round in enumerate(rounds[:-1]):
        next_round = rounds[round_index + 1]
        for match_index, match in enumerate(bracket_round):
            next_match = next_round[match_index // 2]
            match.next_match_id = next_match.id
            if match.is_bye and match.winner_id:
                if match_index % 2 == 0:
                    next_match.home_team_id = match.winner_id
                else:
                    next_match.away_team_id = match.winner_id

    return all_matches
