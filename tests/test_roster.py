"""Verify roster saving through the public tool function.

Tests cover validation, replacement, player identities, and session
isolation without model calls or external services.
"""

from pydantic import JsonValue

from src.application.session_db import ConversationSession
from src.tools.teams.roster import set_roster


def test_save_player_with_server_assigned_id() -> None:
    session: ConversationSession = ConversationSession()

    result: dict[str, JsonValue] = set_roster(
        {
            "players": [
                {"name": "Sara", "rating": 3, "goalkeeper_willing": True}
            ]
        },
        session,
    )

    assert result["ok"] is True
    assert len(session.roster) == 1
    assert session.roster[0].player_id
    assert session.roster[0].name == "Sara"
    assert session.roster[0].rating == 3
    assert session.roster[0].goalkeeper_willing is True
    assert result["players"] == [
        {
            "player_id": session.roster[0].player_id,
            "name": "Sara",
            "rating": 3,
            "goalkeeper_willing": True,
        }
    ]


def test_replace_roster_and_preserve_matching_player_id() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(
        {
            "players": [
                {"name": "Sara", "rating": 3},
                {"name": "Ahmed", "rating": 4},
            ]
        },
        session,
    )
    original_id: str = session.roster[0].player_id

    set_roster(
        {"players": [{"name": "Sara", "rating": 5}]},
        session,
    )

    assert len(session.roster) == 1
    assert session.roster[0].player_id == original_id
    assert session.roster[0].rating == 5


def test_reject_missing_rating_without_changing_roster() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(
        {"players": [{"name": "Sara", "rating": 3}]},
        session,
    )

    result: dict[str, JsonValue] = set_roster(
        {"players": [{"name": "Ahmed"}]},
        session,
    )

    assert result["ok"] is False
    assert len(session.roster) == 1
    assert session.roster[0].name == "Sara"


def test_reject_duplicate_names() -> None:
    session: ConversationSession = ConversationSession()

    result: dict[str, JsonValue] = set_roster(
        {
            "players": [
                {"name": "Sara", "rating": 3},
                {"name": " sara ", "rating": 4},
            ]
        },
        session,
    )

    assert result["ok"] is False
    assert session.roster == ()


def test_keep_rosters_separate_between_sessions() -> None:
    first: ConversationSession = ConversationSession()
    second: ConversationSession = ConversationSession()

    set_roster(
        {"players": [{"name": "Sara", "rating": 3}]},
        first,
    )

    assert len(first.roster) == 1
    assert second.roster == ()


def test_clear_roster() -> None:
    session: ConversationSession = ConversationSession()
    set_roster(
        {"players": [{"name": "Sara", "rating": 3}]},
        session,
    )

    result: dict[str, JsonValue] = set_roster(
        {"players": []},
        session,
    )

    assert result["ok"] is True
    assert session.roster == ()
