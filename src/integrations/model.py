"""Connect the application to Gemini through LiteLLM's Vertex AI provider.

Translate application messages into provider requests and return application-owned
responses. Google Application Default Credentials supply authentication; network
model calls occur only when generate_response is invoked.
"""

from json import dumps
from typing import cast

import litellm
from litellm.types.utils import ChatCompletionMessageToolCall, Choices, ModelResponse
from pydantic import JsonValue, TypeAdapter, ValidationError

from src.application.models import ChatMessage, ToolDefinition, ToolRequest
from src.configuration.constants import constants


def generate_response(
    messages: tuple[ChatMessage, ...],
    tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    """Send conversation history and ready-to-use tool schemas to Gemini.

    Example: (ChatMessage(USER, "Hi"),) -> ChatMessage(ASSISTANT, "Hello")
    when the provider replies with "Hello". USER and ASSISTANT refer to
    constants.roles members. Actual model output varies.
    Tool requests are returned for the agent loop to execute."""

    response = cast(ModelResponse, litellm.completion(
        model=constants.gemini.MODEL.value,
        vertex_location=constants.gemini.LOCATION.value,
        messages=[serialize_message(message) for message in messages],
        stream=False,
        tools=list(tools) if tools else None,
        timeout=30.0,
        num_retries=0,
    ))
    choice = cast(Choices, response.choices[0])
    return ChatMessage(
        role=constants.roles.ASSISTANT,
        content=choice.message.content or "",
        tool_calls=tuple(
            deserialize_tool_request(call) for call in choice.message.tool_calls or ()
        ),
    )


def serialize_message(message: ChatMessage) -> dict[str, JsonValue]:
    """Convert one application message into LiteLLM's message dictionary.

    Example: ChatMessage(USER, "Hi") -> {"role": "user", "content": "Hi"}.
    USER denotes constants.roles.USER. Tool requests also include their IDs,
    names, and JSON argument strings; tool results include the matching call ID."""

    payload = dict(role=message.role.value, content=message.content)
    if message.tool_calls:
        payload["tool_calls"] = [dict(
            id=call.call_id,
            type="function",
            function=dict(name=call.name, arguments=dumps(call.arguments)),
        ) for call in message.tool_calls]
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    return payload


def deserialize_tool_request(call: ChatCompletionMessageToolCall) -> ToolRequest:
    """Convert a provider function call into an executable application request.

    Example: a call with id="c1", name="echo", arguments='{"value": 7}'
    becomes ToolRequest(call_id="c1", name="echo", arguments={"value": 7}).
    Malformed argument text is marked invalid so the harness can record a failure
    and give the model a chance to correct its call. This function does not execute the requested tool."""
    
    try:
        arguments = TypeAdapter(dict[str, JsonValue]).validate_json(call.function.arguments)
    except ValidationError:
        return ToolRequest(call.id, call.function.name, {}, invalid_arguments=True)
    return ToolRequest(call_id=call.id, name=call.function.name, arguments=arguments)
