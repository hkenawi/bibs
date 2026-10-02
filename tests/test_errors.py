"""Exercise external failures through registered tools and the HTTP boundary.

Provider I/O is mocked at its public boundary; application validation and
state changes execute normally. No live credentials or services are needed.
"""

from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import JsonValue

from src.application.session_db import ConversationSession
from src.tools.pitches.search import find_nearby_pitches


@pytest.mark.parametrize(("status", "code", "attempts"), [
    (400, "BAD_REQUEST", 1), (401, "ACCESS_DENIED", 1),
    (403, "ACCESS_DENIED", 1), (429, "RATE_LIMITED", 1),
    (500, "SERVICE_UNAVAILABLE", 1),
])
def test_pitch_http_failures_are_classified_without_response_leaks(
    monkeypatch: pytest.MonkeyPatch, status: int, code: str, attempts: int,
) -> None:
    response = httpx.Response(status, text="private upstream details",
        request=httpx.Request("POST", "https://overpass-api.de/api/interpreter"))
    post = MagicMock(return_value=response)
    monkeypatch.setattr(httpx, "post", post)
    result = find_nearby_pitches(
        {"neighborhood": "Harlem", "city": "New York"}, ConversationSession())
    assert result["error"]["code"] == code
    assert "private upstream details" not in str(result)
    assert post.call_count == attempts
    assert "retryable" not in result["error"]


def test_invalid_model_json_can_be_corrected_in_the_same_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient
    from litellm.types.utils import ModelResponse
    import litellm
    from src.api.bootstrap import create_app

    completion = MagicMock(side_effect=[
        ModelResponse(choices=[{"message": {"role": "assistant", "tool_calls": [{
            "id": "bad", "type": "function", "function": {"name": "balance_soccer_teams", "arguments": "{oops"}
        }]}}]),
        ModelResponse(choices=[{"message": {"role": "assistant", "content": "Please enter three players."}}]),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    response = TestClient(create_app()).post("/chat", json={"message": "Make teams"})
    assert response.json()["tool_calls"][0]["result"]["error"]["code"] == "INVALID_INPUT"
    assert response.json()["response"] == "Please enter three players."



def test_completed_conversation_can_be_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient
    from litellm.types.utils import ModelResponse
    import litellm
    from src.api.bootstrap import create_app

    completion = MagicMock(return_value=ModelResponse(choices=[{
        "message": {"role": "assistant", "content": "Hello"}}]))
    monkeypatch.setattr(litellm, "completion", completion)
    client = TestClient(create_app())
    first = client.post("/chat", json={"message": "Hi"})
    assert first.status_code == 200
    restored = client.get("/session", params={"session_id": first.json()["session_id"]})
    assert restored.json()["turns"][0]["response"] == "Hello"
    assert completion.call_count == 1


@pytest.mark.parametrize("count", [0, 1, 2, 23])
def test_roster_rejects_out_of_range_counts_without_mutation(count: int) -> None:
    from src.tools.teams.roster import set_roster
    session = ConversationSession()
    result = set_roster({"players": [
        {"name": f"Player {index}", "rating": 3} for index in range(count)
    ]}, session)
    assert result["ok"] is False
    assert session.roster == ()



def test_saved_roster_and_tool_records_survive_a_later_model_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from json import dumps
    from fastapi.testclient import TestClient
    from litellm.types.utils import ModelResponse
    import litellm
    from src.api.bootstrap import create_app

    players = [{"name": name, "rating": 3} for name in ("Sara", "Ahmed", "Maya")]
    completion = MagicMock(side_effect=[
        ModelResponse(choices=[{"message": {"role": "assistant", "tool_calls": [{
            "id": "save", "type": "function", "function": {"name": "set_roster", "arguments": dumps({"players": players})}
        }]}}]), RuntimeError("private credentials"),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    client = TestClient(create_app())
    response = client.post("/chat", json={"message": "Save my roster"})
    assert response.status_code == 200
    assert response.json()["tool_calls"][0]["result"]["ok"] is True
    assert "preserved" in response.json()["response"]
    assert "private credentials" not in response.text
    restored = client.get("/session", params={"session_id": response.json()["session_id"]})
    assert len(restored.json()["state"]["roster"]) == 3
    assert restored.json()["turns"][0]["tool_calls"] == response.json()["tool_calls"]


