"""Verify valid roster replacement and rejected edits through the tool handler.

Fixtures meet the application's three-player minimum. These tests verify stable
player identities, validation before mutation, and independent session state.
"""

from pydantic import JsonValue
import pytest

from src.application.session_db import ConversationSession
from src.tools.teams.roster import set_roster


def create_roster_arguments(rating: int = 3) -> dict[str, JsonValue]:
    """Build a valid three-player roster with a willing goalkeeper."""
    return {"players": [
        {"name": "Sara", "rating": rating, "goalkeeper_willing": True},
        {"name": "Ahmed", "rating": 4},
        {"name": "Maya", "rating": 2},
    ]}


def test_replace_roster_and_preserve_matching_player_id() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), session)
    original_id: str = session.roster[0].player_id
    session.home = session.roster[:2]
    session.away = session.roster[2:]
    set_roster(create_roster_arguments(rating=5), session)
    assert session.roster[0].player_id == original_id
    assert session.roster[0].rating == 5
    assert session.home == session.away == ()


@pytest.mark.parametrize("invalid_player", [
    {"name": "Sara"},
    {"name": "Sara", "rating": 0},
    {"name": "Sara", "rating": 6},
    {"name": "Sara", "rating": True},
])
def test_reject_invalid_player_without_changing_roster(invalid_player: dict[str, JsonValue]) -> None:
    session: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), session)
    result: dict[str, JsonValue] = set_roster({"players": [
        invalid_player, {"name": "Ahmed", "rating": 4}, {"name": "Maya", "rating": 2},
    ]}, session)
    assert result["ok"] is False
    assert len(session.roster) == 3
    assert session.roster[0].rating == 3


def test_reject_duplicate_names() -> None:
    session: ConversationSession = ConversationSession()
    result: dict[str, JsonValue] = set_roster({"players": [
        {"name": "Sara", "rating": 3}, {"name": " sara ", "rating": 4}, {"name": "Maya", "rating": 2},
    ]}, session)
    assert result["ok"] is False
    assert session.roster == ()


@pytest.mark.parametrize("count", [2, 23])
def test_roster_rejects_out_of_range_counts_without_mutation(count: int) -> None:
    from src.tools.teams.roster import set_roster
    session: ConversationSession = ConversationSession()
    result: dict[str, JsonValue] = set_roster({"players": [
        {"name": f"Player {index}", "rating": 3} for index in range(count)
    ]}, session)
    assert result["ok"] is False
    assert session.roster == ()
