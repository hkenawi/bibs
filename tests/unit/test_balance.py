"""Verify team balancing through the public tool handler.

Tests use validated session rosters without model calls or external services.
"""

from pydantic import JsonValue
import pytest

from src.application.session_db import ConversationSession
from src.tools.teams.balance import balance_soccer_teams
from src.tools.teams.models import RosterPlayer


def test_balance_and_save_teams_with_equal_total_ratings() -> None:
    session: ConversationSession = ConversationSession(
        roster=(
            RosterPlayer(player_id="p1", name="Ahmed", rating=5),
            RosterPlayer(player_id="p2", name="Sara", rating=4),
            RosterPlayer(player_id="p3", name="Omar", rating=2),
            RosterPlayer(player_id="p4", name="Maya", rating=1),
        )
    )

    result: dict[str, JsonValue] = balance_soccer_teams({}, session)

    assert result["ok"] is True
    assert result["home_total"] == 6
    assert result["away_total"] == 6
    assert result["rating_gap"] == 0
    assert {player.player_id for player in session.home} == {"p1", "p4"}
    assert {player.player_id for player in session.away} == {"p2", "p3"}


@pytest.mark.parametrize(("ratings", "keepers", "expected_gap"), [
    ((5, 4, 3, 2, 1), (), 1),
    ((5, 1, 3, 3), (0, 1), 4),
])
def test_balance_respects_team_sizes_and_goalkeeper_constraints(
    ratings: tuple[int, ...], keepers: tuple[int, ...], expected_gap: int,
) -> None:
    """Find the best feasible split for odd rosters and constrained keepers."""
    session: ConversationSession = ConversationSession(roster=tuple(
        RosterPlayer(player_id=f"p{index}", name=f"Player {index}", rating=rating,
                     goalkeeper_willing=index in keepers)
        for index, rating in enumerate(ratings)
    ))
    result: dict[str, JsonValue] = balance_soccer_teams(
        {"dedicated_goalkeepers": bool(keepers)}, session,
    )
    assert result["ok"] is True
    assert result["rating_gap"] == expected_gap
    assert len(session.home) == (len(ratings) + 1) // 2
    assert len(session.away) == len(ratings) // 2
    assert {player.player_id for player in session.home}.isdisjoint(
        (player.player_id for player in session.away),
    )
    assert set(session.home + session.away) == set(session.roster)
    if keepers:
        assert any(player.goalkeeper_willing for player in session.home)
        assert any(player.goalkeeper_willing for player in session.away)


def test_missing_goalkeeper_leaves_saved_teams_unchanged() -> None:
    """An infeasible keeper request must preserve the last successful split."""
    session: ConversationSession = ConversationSession(roster=(
        RosterPlayer(player_id="p1", name="Sara", rating=5, goalkeeper_willing=True),
        RosterPlayer(player_id="p2", name="Ahmed", rating=4),
        RosterPlayer(player_id="p3", name="Maya", rating=1),
    ))
    balance_soccer_teams({}, session)
    original_home: tuple[RosterPlayer, ...] = session.home
    original_away: tuple[RosterPlayer, ...] = session.away
    result: dict[str, JsonValue] = balance_soccer_teams({"dedicated_goalkeepers": True}, session)
    assert result["ok"] is False
    assert session.home == original_home
    assert session.away == original_away
    assert session.dedicated_goalkeepers is False
