"""Verify the browser-facing chat contract through the real HTTP application.

These integration tests exercise public routes without network model requests;
the default application uses the explicitly identified local demo adapter."""

from fastapi.testclient import TestClient
from httpx import Response
import pytest

from src.api import create_app
from src.application import service
from src.application.models import ChatMessage, ToolDefinition
from src.configuration import constants


def test_chat_returns_required_fields_without_tool_execution() -> None:
    client: TestClient = TestClient(create_app())
    response: Response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert set(response.json()) == {"response", "session_id", "tool_calls"}
    assert response.json()["session_id"]
    assert "demo" in response.json()["response"].lower()
    assert response.json()["tool_calls"] == []


def generate_history_response(
    messages: tuple[ChatMessage, ...], tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    return ChatMessage(constants.roles.ASSISTANT, " | ".join(message.content for message in messages))

def test_follow_up_uses_history_and_new_sessions_are_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "generate_response", generate_history_response)
    client: TestClient = TestClient(create_app())
    first: Response = client.post("/chat", json={"message": "Alice"})
    follow_up: Response = client.post(
        "/chat", json={"message": "Bob", "session_id": first.json()["session_id"]}
    )
    independent: Response = client.post("/chat", json={"message": "Charlie"})
    assert follow_up.json()["response"] == "Alice | Alice | Bob"
    assert follow_up.json()["session_id"] == first.json()["session_id"]
    assert independent.json()["response"] == "Charlie"


def test_unknown_session_is_explicitly_rejected() -> None:
    client: TestClient = TestClient(create_app())
    response: Response = client.post(
        "/chat", json={"message": "Hello", "session_id": "expired"}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_EXPIRED"


def test_local_browser_entry_and_health_are_available() -> None:
    client: TestClient = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok", "model_mode": "demo"}
    page: Response = client.get("/")
    assert page.status_code == 200
    assert "Local demo" in page.text
    assert client.get("/static/chat.js").status_code == 200


def test_blank_message_is_rejected() -> None:
    client: TestClient = TestClient(create_app())
    assert client.post("/chat", json={"message": "   "}).status_code == 422
