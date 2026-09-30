"""Define conversation data and model/tool interfaces for bibs.

The application and provider adapters share message dataclasses. Tool schemas
are typed dictionaries in the format accepted directly by LiteLLM, without
importing provider SDK types into the application."""

from dataclasses import dataclass
from typing import Protocol, TypedDict

from pydantic import JsonValue

from src.configuration import MessageRole
from src.configuration.constants import ProviderToolType


class ToolFunctionDefinition(TypedDict):
    """Describe a callable tool and the JSON schema of its arguments."""

    name: str
    description: str
    parameters: dict[str, JsonValue]


class ToolDefinition(TypedDict):
    """Declare a tool in LiteLLM's request format; no conversion is needed."""

    type: ProviderToolType
    function: ToolFunctionDefinition


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
        """Validate arguments and execute this tool, returning a JSON object.

        Example for an echo implementation: {"value": 7} -> {"value": 7}.
        Each implementation defines its own argument schema and result fields.
        """
        ...
