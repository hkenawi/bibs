"""Generate model responses for bibs.

Currently returns a local demo response. Gemini integration will be added here."""

from src.application.models import ChatMessage, ToolDefinition
from src.configuration import constants


def generate_response(
    messages: tuple[ChatMessage, ...],
    tools: tuple[ToolDefinition, ...] = (),
) -> ChatMessage:
    # TODO: Implement the Gemini connection.
    return ChatMessage(
        role=constants.roles.ASSISTANT,
        content=(
            "Local demo mode — Gemini is not connected. "
            f"You said: {messages[-1].content}"
        ),
    )
