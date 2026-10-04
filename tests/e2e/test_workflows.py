"""Verify bibs workflows across the full HTTP backend and provider adapter.

Real routes, tool dispatch, validation, calculations, and session storage run
with controlled responses only at LiteLLM and external HTTP boundaries. These
checks cover backend flows rather than browser clicks or live service uptime.
"""

from json import dumps, loads
from unittest.mock import MagicMock

import httpx
import litellm
import pytest
from fastapi.testclient import TestClient
from litellm.types.utils import ModelResponse
from pydantic import JsonValue

from src.api.bootstrap import create_app


def create_tool_reply(calls: list[tuple[str, str, dict[str, JsonValue]]]) -> ModelResponse:
    """Build an external provider response requesting one or more tools."""
    return ModelResponse(choices=[{"message": {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": call_id, "type": "function", "function": {
            "name": name, "arguments": dumps(arguments),
        }} for call_id, name, arguments in calls],
    }}])


def create_text_reply(content: str) -> ModelResponse:
    """Build the final external provider response for a completed turn."""
    return ModelResponse(choices=[{"message": {"role": "assistant", "content": content}}])


def test_save_balance_correct_and_restore_roster_through_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    players: list[JsonValue] = [
        {"name": "Ahmed", "rating": 5}, {"name": "Sara", "rating": 4},
        {"name": "Omar", "rating": 2}, {"name": "Maya", "rating": 1},
    ]
    corrected_players: list[JsonValue] = [
        {"name": "Ahmed", "rating": 3}, *players[1:],
    ]
    completion: MagicMock = MagicMock(side_effect=[
        create_tool_reply([
            ("save", "set_roster", {"players": players}),
            ("balance", "balance_soccer_teams", {}),
        ]),
        create_text_reply("Teams ready."),
        create_tool_reply([("correct", "set_roster", {"players": corrected_players})]),
        create_text_reply("Roster corrected."),
        create_text_reply("Start with your players."),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    client: TestClient = TestClient(create_app())
    initial: httpx.Response = client.post("/chat", json={"message": "Save these four players and make fair teams."})
    assert initial.status_code == 200
    assert initial.json()["response"] == "Teams ready."
    records: list[dict[str, JsonValue]] = initial.json()["tool_calls"]
    assert [record["name"] for record in records] == ["set_roster", "balance_soccer_teams"]
    assert records[1]["result"]["rating_gap"] == 0
    assert [message["tool_call_id"] for message in completion.call_args.kwargs["messages"]
            if message["role"] == "tool"] == ["save", "balance"]
    assert {tool["function"]["name"] for tool in completion.call_args.kwargs["tools"]} == {
        "set_roster", "balance_soccer_teams", "find_nearby_pitches",
    }
    session_id: str = initial.json()["session_id"]
    balanced: dict[str, JsonValue] = client.get("/session", params={"session_id": session_id}).json()
    assert len(balanced["state"]["home"]) == len(balanced["state"]["away"]) == 2
    original_player_id: str = balanced["state"]["roster"][0]["player_id"]

    corrected: httpx.Response = client.post("/chat", json={
        "session_id": session_id, "message": "Change Ahmed to rating 3.",
    })
    assert corrected.status_code == 200
    restored: dict[str, JsonValue] = client.get("/session", params={"session_id": session_id}).json()
    assert restored["state"]["roster"][0]["player_id"] == original_player_id
    assert restored["state"]["roster"][0]["rating"] == 3
    assert restored["state"]["home"] == restored["state"]["away"] == []
    assert len(restored["turns"]) == 2
    assert restored["turns"][0]["tool_calls"] == records

    independent: httpx.Response = client.post("/chat", json={"message": "Hello"})
    independent_state: dict[str, JsonValue] = client.get(
        "/session", params={"session_id": independent.json()["session_id"]},
    ).json()
    assert independent_state["state"]["roster"] == []


def test_pitch_search_returns_map_links_through_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "get", MagicMock(return_value=httpx.Response(
        200, json=[{"display_name": "Harlem, New York", "boundingbox": ["40.8", "40.83", "-73.96", "-73.93"]}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )))
    monkeypatch.setattr(httpx, "post", MagicMock(return_value=httpx.Response(
        200, json={"elements": [{"type": "way", "id": 123, "tags": {"name": "Soccer Field"}}]},
        request=httpx.Request("POST", "https://overpass-api.de/api/interpreter"),
    )))
    completion: MagicMock = MagicMock(side_effect=[
        create_tool_reply([("pitch", "find_nearby_pitches", {"neighborhood": "Harlem", "city": "New York"})]),
        create_text_reply("Found a soccer field in Harlem."),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    response: httpx.Response = TestClient(create_app()).post("/chat", json={"message": "Find pitches in Harlem, New York."})
    assert response.status_code == 200
    result: dict[str, JsonValue] = response.json()["tool_calls"][0]["result"]
    assert result["ok"] is True
    assert result["searched_location"] == "Harlem, New York"
    assert result["pitches"] == [{"name": "Soccer Field", "map_url": "https://www.openstreetmap.org/way/123"}]
    provider_result: dict[str, JsonValue] = completion.call_args.kwargs["messages"][-1]
    assert provider_result["tool_call_id"] == "pitch"
    assert loads(provider_result["content"]) == result
