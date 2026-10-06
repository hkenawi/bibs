"""Exercise browser-facing HTTP contracts through the complete backend.

Only external model calls are replaced. Routing, provider conversion,
conversation history, and session isolation run normally. These backend
end-to-end checks do not automate browser interactions."""

import pytest
import litellm

from httpx import Response
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from litellm.types.utils import ModelResponse

from src.api.bootstrap import create_app


def test_follow_up_uses_history_and_new_sessions_are_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completion: MagicMock = MagicMock(
        side_effect=[
            ModelResponse(
                choices=[{"message": {"role": "assistant", "content": reply}}]
            )
            for reply in ("Hello Alice", "Hello Bob", "Hello Charlie")
        ]
    )
    monkeypatch.setattr(
        litellm,
        "completion",
        completion,
    )
    client: TestClient = TestClient(create_app())
    first: Response = client.post("/chat", json={"message": "Alice"})
    follow_up: Response = client.post(
        "/chat",
        json={"message": "Bob", "session_id": first.json()["session_id"]},
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["response"] == "Hello Bob"
    assert follow_up.json()["session_id"] == first.json()["session_id"]
    assert completion.call_args.kwargs["messages"] == [
        {"role": "user", "content": "Alice"},
        {"role": "assistant", "content": "Hello Alice"},
        {"role": "user", "content": "Bob"},
    ]
    independent: Response = client.post(
        "/chat",
        json={"message": "Charlie"},
    )
    assert independent.json()["session_id"] != first.json()["session_id"]
    assert independent.json()["tool_calls"] == []
    assert completion.call_args.kwargs["messages"] == [
        {"role": "user", "content": "Charlie"}
    ]


def test_unknown_session_is_explicitly_rejected() -> None:
    client: TestClient = TestClient(create_app())
    response: Response = client.post(
        "/chat",
        json={"message": "Hello", "session_id": "expired"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_EXPIRED"


def test_browser_entry_and_chat_assets_are_served() -> None:
    client: TestClient = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert client.get("/static/chat.js").status_code == 200


def test_blank_message_is_rejected() -> None:
    client: TestClient = TestClient(create_app())
    assert client.post("/chat", json={"message": "   "}).status_code == 422
