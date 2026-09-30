"""Verify team balancing through the public tool handler.

Tests use validated session rosters without model calls or external services.
"""

from pydantic import JsonValue

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
