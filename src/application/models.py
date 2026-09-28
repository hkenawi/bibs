"""Define conversation data and model/tool interfaces for bibs.

The application and provider adapters share these types so the agent loop
can operate without depending on a particular model SDK."""

from dataclasses import dataclass
from typing import Protocol

from pydantic import JsonValue

from src.configuration import MessageRole


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, JsonValue]


@dataclass(frozen=True)
class ToolRequest:
    call_id: str
    name: str
    arguments: dict[str, JsonValue]


@dataclass(frozen=True)
class ToolRecord:
    name: str
    args: dict[str, JsonValue]
    result: dict[str, JsonValue]


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str
    tool_calls: tuple[ToolRequest, ...] = ()
    tool_call_id: str | None = None


class ChatTool(Protocol):
    definition: ToolDefinition

    def execute_tool(
        self,
        arguments: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        """Validate the supplied arguments and return the tool result."""
        ...
