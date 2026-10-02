"""Verify model-driven tool activity at the public HTTP boundary.

Controlled model and tool adapters replace external capabilities. Assertions use
observable response records and conversation messages, not private service state."""

from fastapi.testclient import TestClient
from httpx import Response
from pydantic import JsonValue
import pytest

from src.api.bootstrap import create_app
from src.application import service
from src.application.models import (
    ChatMessage, ChatTool, ToolDefinition, ToolRequest,
)
from src.configuration.constants import constants


echo_definition = {
    "type": "function",
    "function": {
        "name": "echo", "description": "Return a supplied value for a contract test.",
        "parameters": {"type": "object", "properties": {"value": {"type": "integer"}},
                       "required": ["value"], "additionalProperties": False},
    },
}

def echo_value(arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Echo arguments: {"value": 7} -> {"ok": True, "data": {"value": 7}}."""
    return {"ok": True, "data": arguments}


echo_tool = {"definition": echo_definition, "handler": echo_value}


def generate_tool_response(
    messages: tuple[ChatMessage, ...], tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    if messages[-1].tool_call_id == "second":
        assert messages[-2].tool_call_id == "first"
        assert messages[-3].tool_calls[0].call_id == "first"
        return ChatMessage(constants.roles.ASSISTANT, "Both results received.")
    assert tools[0]["function"]["name"] == "echo"
    return ChatMessage(constants.roles.ASSISTANT, "", tool_calls=(
        ToolRequest("first", "echo", {"value": 7}),
        ToolRequest("second", "echo", {"value": 9}),
    ))

def test_executed_tools_are_recorded_in_order_and_returned_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_tool_response)
    client = TestClient(create_app(tools=(echo_tool,)))
    response = client.post("/chat", json={"message": "Run the test tools"})
    assert response.status_code == 200
    assert response.json()["response"] == "Both results received."
    assert response.json()["tool_calls"] == [
        {"name": "echo", "args": {"value": 7}, "result": {"ok": True, "data": {"value": 7}}},
        {"name": "echo", "args": {"value": 9}, "result": {"ok": True, "data": {"value": 9}}},
    ]


def generate_unknown_tool_response(
    messages: tuple[ChatMessage, ...], tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    return ChatMessage(constants.roles.ASSISTANT, "", (ToolRequest("unknown", "missing", {}),))

def test_unknown_tool_is_recorded_for_model_correction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_unknown_tool_response)
    client = TestClient(create_app())
    response = client.post("/chat", json={"message": "Try a tool"})
    assert response.status_code == 200
    assert response.json()["tool_calls"][0]["result"]["error"]["code"] == "UNKNOWN_TOOL"


def generate_repeating_tool_response(
    messages: tuple[ChatMessage, ...], tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    return ChatMessage(constants.roles.ASSISTANT, "", (ToolRequest("repeat", "echo", {"value": 7}),))

def test_loop_stops_before_executing_tools_beyond_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_repeating_tool_response)
    client = TestClient(create_app(
        tools=(echo_tool,),
    ))
    response = client.post("/chat", json={"message": "Repeat"})
    assert "limit" in response.json()["response"]
    assert len(response.json()["tool_calls"]) == 4


def generate_failing_response(
    messages: tuple[ChatMessage, ...], tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    raise RuntimeError("secret-provider-detail")

def test_provider_failure_returns_safe_chat_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_failing_response)
    client = TestClient(create_app())
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert set(response.json()) == {"response", "session_id", "tool_calls"}
    assert "secret-provider-detail" not in response.text
    assert "try again" in response.json()["response"].lower()


def reject_arguments(arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Reject input: any argument dictionary -> ValueError."""
    raise ValueError("Invalid test input")


failing_tool = {"definition": echo_definition, "handler": reject_arguments}


def test_tool_failure_returns_safe_record(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_repeating_tool_response)
    client = TestClient(create_app(
        tools=(failing_tool,),
    ))
    response = client.post("/chat", json={"message": "Run the tool"})
    assert response.status_code == 200
    assert response.json()["tool_calls"][0]["result"]["error"]["code"] == "TOOL_FAILED"
    assert "Invalid test input" not in response.text
