"""Verify recovery through the complete HTTP chat application.

Only external model calls are replaced. Real provider conversion, tool
execution, session persistence, and safe error handling run together.
"""

from unittest.mock import MagicMock

import pytest
import litellm
from json import dumps
from fastapi.testclient import TestClient
from httpx import Response
from litellm.types.utils import ModelResponse
from pydantic import JsonValue

from src.api.bootstrap import create_app


def test_invalid_model_json_can_be_corrected_in_the_same_turn(monkeypatch: pytest.MonkeyPatch) -> None:

    completion: MagicMock = MagicMock(side_effect=[
        ModelResponse(choices=[{"message": {"role": "assistant", "tool_calls": [{
            "id": "bad", "type": "function", "function": {"name": "balance_soccer_teams", "arguments": "{oops"}
        }]}}]),
        ModelResponse(choices=[{"message": {"role": "assistant", "content": "Please enter three players."}}]),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    response: Response = TestClient(create_app()).post("/chat", json={"message": "Make teams"})
    assert response.json()["tool_calls"][0]["result"]["error"]["code"] == "INVALID_INPUT"
    assert response.json()["response"] == "Please enter three players."


def test_saved_roster_and_tool_records_survive_a_later_model_failure(monkeypatch: pytest.MonkeyPatch) -> None:

    players: list[JsonValue] = [{"name": name, "rating": 3} for name in ("Sara", "Ahmed", "Maya")]
    completion: MagicMock = MagicMock(side_effect=[
        ModelResponse(choices=[{"message": {"role": "assistant", "tool_calls": [{
            "id": "save", "type": "function", "function": {"name": "set_roster", "arguments": dumps({"players": players})}
        }]}}]), RuntimeError("private credentials"),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    client: TestClient = TestClient(create_app())
    response: Response = client.post("/chat", json={"message": "Save my roster"})
    assert response.status_code == 200
    assert response.json()["tool_calls"][0]["result"]["ok"] is True
    assert "preserved" in response.json()["response"]
    assert "private credentials" not in response.text
    restored: Response = client.get("/session", params={"session_id": response.json()["session_id"]})
    assert len(restored.json()["state"]["roster"]) == 3
    assert restored.json()["turns"][0]["tool_calls"] == response.json()["tool_calls"]
