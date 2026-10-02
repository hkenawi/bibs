"""Verify roster tool execution through the chat HTTP interface.

A controlled model response requests roster saving. Real routing,
tool registration, session storage, and roster validation execute.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import JsonValue

from src.api.bootstrap import create_app
from src.application import service
from src.application.models import ChatMessage, ToolRequest
from src.configuration.constants import constants


def test_save_rosters_in_the_correct_chat_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completion: MagicMock = MagicMock(
        side_effect=[
            ChatMessage(
                constants.roles.ASSISTANT,
                "",
                (
                    ToolRequest(
                        "save-first",
                        "set_roster",
                        {"players": [{"name": "Sara", "rating": 3}, {"name": "Ahmed", "rating": 4}, {"name": "Maya", "rating": 2}]},
                    ),
                ),
            ),
            ChatMessage(constants.roles.ASSISTANT, "Roster saved."),
            ChatMessage(
                constants.roles.ASSISTANT,
                "",
                (
                    ToolRequest(
                        "save-second",
                        "set_roster",
                        {"players": [{"name": "Sara", "rating": 2}, {"name": "Ahmed", "rating": 4}, {"name": "Maya", "rating": 2}]},
                    ),
                ),
            ),
            ChatMessage(constants.roles.ASSISTANT, "Roster saved."),
            ChatMessage(
                constants.roles.ASSISTANT,
                "",
                (
                    ToolRequest(
                        "update-first",
                        "set_roster",
                        {"players": [{"name": "Sara", "rating": 5}, {"name": "Ahmed", "rating": 4}, {"name": "Maya", "rating": 2}]},
                    ),
                ),
            ),
            ChatMessage(constants.roles.ASSISTANT, "Roster updated."),
        ]
    )
    monkeypatch.setattr(service, "generate_response", completion)

    with TestClient(create_app()) as client:
        first: Response = client.post(
            "/chat",
            json={"message": "Sara, 3"},
        )
        assert first.status_code == 200
        assert first.json()["tool_calls"][0]["result"]["ok"] is True

        first_session_id: str = first.json()["session_id"]
        first_player_id: str = (
            first.json()["tool_calls"][0]["result"]["players"][0]["player_id"]
        )

        second: Response = client.post(
            "/chat",
            json={"message": "Sara, 2"},
        )
        assert second.status_code == 200
        assert second.json()["session_id"] != first_session_id
        assert (
            second.json()["tool_calls"][0]["result"]["players"][0]["player_id"]
            != first_player_id
        )

        updated: Response = client.post(
            "/chat",
            json={
                "session_id": first_session_id,
                "message": "Change Sara to 5",
            },
        )
        assert updated.status_code == 200
        updated_players: list[dict[str, JsonValue]] = updated.json()["tool_calls"][0]["result"]["players"]
        assert updated_players[0] == {
            "player_id": first_player_id, "name": "Sara", "rating": 5, "goalkeeper_willing": False,
        }
        assert len(updated_players) == 3
