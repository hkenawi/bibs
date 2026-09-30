"""Verify default tool discovery and placeholder execution through HTTP.

Only LiteLLM is replaced, so requests exercise registration, message conversion,
the agent loop, and the real placeholder tools without calling Google Cloud.
"""

from unittest.mock import MagicMock
from json import dumps, loads

import litellm
from fastapi.testclient import TestClient
from httpx import Response
from litellm.types.utils import ModelResponse
import pytest

from src.api.bootstrap import create_app
from src.application.models import ToolDefinition
from pydantic import JsonValue


def test_default_tools_are_advertised_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """A chat question sends five described tool schemas to the provider."""
    completion: MagicMock = MagicMock(return_value=ModelResponse(choices=[{
        "message": {"role": "assistant", "content": "Five tools are available."},
    }]))
    monkeypatch.setattr(litellm, "completion", completion)
    response: Response = TestClient(create_app()).post(
        "/chat", json={"message": "What tools do you have access to?"},
    )
    assert response.status_code == 200
    tool: ToolDefinition
    assert {tool["function"]["name"] for tool in completion.call_args.kwargs["tools"]} == {
        "set_roster", "balance_soccer_teams", "compare_team_options",
        "rebalance_with_minimal_swaps", "find_nearby_pitches",
    }
    for tool in completion.call_args.kwargs["tools"]:
        assert tool["type"] == "function"
        assert "not implemented" not in tool["function"]["description"].lower()
        assert tool["function"]["parameters"]["type"] == "object"


def test_explicit_empty_registry_disables_default_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit tools=() sends no tools to the model."""
    completion: MagicMock = MagicMock(return_value=ModelResponse(choices=[{
        "message": {"role": "assistant", "content": "No tools."},
    }]))
    monkeypatch.setattr(litellm, "completion", completion)
    response: Response = TestClient(create_app(tools=())).post("/chat", json={"message": "Hi"})
    assert response.status_code == 200
    assert completion.call_args.kwargs["tools"] is None


@pytest.mark.parametrize(("tool_name", "arguments"), [
    ("compare_team_options", {"home_player_id": "p1", "away_player_id": "p2"}),
    ("rebalance_with_minimal_swaps", {"priority": "fewest_changes", "removals": ["p1"]}),
    ("find_nearby_pitches", {"neighborhood": "Harlem", "city": "New York"}),
])
def test_placeholder_call_is_recorded_and_returned_to_model(
    monkeypatch: pytest.MonkeyPatch, tool_name: str, arguments: dict[str, JsonValue],
) -> None:
    """A model call yields a literal not-implemented result in the record and follow-up."""
    completion: MagicMock = MagicMock(side_effect=[
        ModelResponse(choices=[{"message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": "placeholder-call", "type": "function", "function": {
                "name": tool_name, "arguments": dumps(arguments),
            }}]}, "finish_reason": "tool_calls"}]),
        ModelResponse(choices=[{"message": {"role": "assistant", "content": "This tool is not implemented yet."}}]),
    ])
    monkeypatch.setattr(litellm, "completion", completion)
    response: Response = TestClient(create_app()).post("/chat", json={"message": "Try this tool"})
    assert response.status_code == 200
    assert response.json()["response"] == "This tool is not implemented yet."
    assert len(response.json()["tool_calls"]) == 1
    record: dict[str, JsonValue] = response.json()["tool_calls"][0]
    assert record["name"] == tool_name
    assert record["args"] == arguments
    result: dict[str, JsonValue] = response.json()["tool_calls"][0]["result"]
    assert result == {"ok": False, "error": "Not implemented"}
    assert loads(completion.call_args.kwargs["messages"][-1]["content"]) == result
    assert completion.call_args.kwargs["messages"][-1]["tool_call_id"] == "placeholder-call"
