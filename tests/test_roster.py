"""Verify valid roster replacement and rejected edits through the tool handler.

Fixtures meet the application's three-player minimum. These tests verify stable
player identities, validation before mutation, and independent session state.
"""

from pydantic import JsonValue

from src.application.session_db import ConversationSession
from src.tools.teams.roster import set_roster


def create_roster_arguments(rating: int = 3) -> dict[str, JsonValue]:
    """Build a valid three-player roster with a willing goalkeeper."""
    return {"players": [
        {"name": "Sara", "rating": rating, "goalkeeper_willing": True},
        {"name": "Ahmed", "rating": 4},
        {"name": "Maya", "rating": 2},
    ]}


def test_save_player_with_server_assigned_id() -> None:
    session: ConversationSession = ConversationSession()
    result: dict[str, JsonValue] = set_roster(create_roster_arguments(), session)
    assert result["ok"] is True
    assert len(session.roster) == 3
    assert session.roster[0].player_id
    assert session.roster[0].name == "Sara"
    assert session.roster[0].goalkeeper_willing is True
    assert result["players"] == [player.model_dump(mode="json") for player in session.roster]


def test_replace_roster_and_preserve_matching_player_id() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), session)
    original_id: str = session.roster[0].player_id
    set_roster(create_roster_arguments(rating=5), session)
    assert session.roster[0].player_id == original_id
    assert session.roster[0].rating == 5


def test_reject_missing_rating_without_changing_roster() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), session)
    result: dict[str, JsonValue] = set_roster({"players": [
        {"name": "Sara"}, {"name": "Ahmed", "rating": 4}, {"name": "Maya", "rating": 2},
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


def test_keep_rosters_separate_between_sessions() -> None:
    first: ConversationSession = ConversationSession()
    second: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), first)
    assert len(first.roster) == 3
    assert second.roster == ()


def test_reject_empty_roster_without_erasing_saved_players() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(create_roster_arguments(), session)
    result: dict[str, JsonValue] = set_roster({"players": []}, session)
    assert result["ok"] is False
    assert len(session.roster) == 3
