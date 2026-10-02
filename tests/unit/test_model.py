"""Verify the public Gemini adapter without contacting Google Cloud.

Only LiteLLM's external completion boundary is mocked. Tests exercise the
application-owned generate_response interface using real SDK response objects.
"""

from unittest.mock import MagicMock

import litellm
from litellm.types.utils import ModelResponse
import pytest

from src.application.models import ChatMessage, ToolDefinition, ToolRequest
from src.configuration.constants import constants
from src.integrations.model import generate_response


@pytest.fixture
def completion_mock(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    completion: MagicMock = MagicMock(return_value=ModelResponse(choices=[{
        "message": {"role": "assistant", "content": "Hello from Gemini."},
        "finish_reason": "stop",
    }]))
    monkeypatch.setattr(litellm, "completion", completion)
    return completion


def test_text_reply_becomes_assistant_message(completion_mock: MagicMock) -> None:
    reply: ChatMessage = generate_response((ChatMessage(constants.roles.USER, "Hi"),))
    assert reply == ChatMessage(constants.roles.ASSISTANT, "Hello from Gemini.")


def test_sends_configured_model_and_ordered_history(completion_mock: MagicMock) -> None:
    generate_response((
        ChatMessage(constants.roles.USER, "Remember Alice"),
        ChatMessage(constants.roles.ASSISTANT, "I will."),
        ChatMessage(constants.roles.USER, "Who?"),
    ))
    assert completion_mock.call_args.kwargs == {
        "model": "vertex_ai/gemini-3.5-flash-lite",
        "vertex_location": "global",
        "stream": False,
        "timeout": 30.0,
        "num_retries": 0,
        "tools": None,
        "messages": [
            {"role": "user", "content": "Remember Alice"},
            {"role": "assistant", "content": "I will."},
            {"role": "user", "content": "Who?"},
        ],
    }


def test_sends_available_tool_definitions(completion_mock: MagicMock) -> None:
    definition: ToolDefinition = {
        "type": "function",
        "function": {
            "name": "weather", "description": "Get weather",
            "parameters": {"type": "object"},
        },
    }
    generate_response((ChatMessage(constants.roles.USER, "Check weather"),), (
        definition,
    ))
    assert completion_mock.call_args.kwargs["tools"] == [{
        "type": "function",
        "function": {
            "name": "weather", "description": "Get weather",
            "parameters": {"type": "object"},
        },
    }]


def test_tool_calls_preserve_ids_and_parse_arguments(completion_mock: MagicMock) -> None:
    completion_mock.return_value = ModelResponse(choices=[{
        "message": {
            "role": "assistant", "content": None,
            "tool_calls": [
                {"id": "call-1", "type": "function", "function": {
                    "name": "weather", "arguments": '{"city": "New York"}',
                }},
                {"id": "call-2", "type": "function", "function": {
                    "name": "weather", "arguments": '{"city": "Boston"}',
                }},
            ],
        },
        "finish_reason": "tool_calls",
    }])
    reply: ChatMessage = generate_response((ChatMessage(constants.roles.USER, "Weather?"),))
    assert reply == ChatMessage(constants.roles.ASSISTANT, "", (
        ToolRequest("call-1", "weather", {"city": "New York"}),
        ToolRequest("call-2", "weather", {"city": "Boston"}),
    ))


def test_tool_results_retain_matching_call_ids(completion_mock: MagicMock) -> None:
    generate_response((
        ChatMessage(constants.roles.ASSISTANT, "", (
            ToolRequest("call-1", "weather", {"city": "New York"}),
        )),
        ChatMessage(constants.roles.TOOL, '{"temperature": 20}', tool_call_id="call-1"),
    ))
    assert completion_mock.call_args.kwargs["messages"] == [
        {"role": "assistant", "content": "", "tool_calls": [{
            "id": "call-1", "type": "function",
            "function": {"name": "weather", "arguments": '{"city": "New York"}'},
        }]},
        {"role": "tool", "content": '{"temperature": 20}', "tool_call_id": "call-1"},
    ]


def test_provider_failure_reaches_the_harness(completion_mock: MagicMock) -> None:
    failure: RuntimeError = RuntimeError("Authentication failed")
    completion_mock.side_effect = failure
    with pytest.raises(RuntimeError) as raised:
        generate_response((ChatMessage(constants.roles.USER, "Hello"),))
    assert raised.value is failure
    assert completion_mock.call_count == 1
