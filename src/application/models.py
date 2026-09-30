"""Define conversation data and model/tool interfaces for bibs.

The application and provider adapters share message dataclasses. Tool schemas
are typed dictionaries in the format accepted directly by LiteLLM, without
importing provider SDK types into the application."""

from dataclasses import dataclass
from collections.abc import Callable
from typing import Literal, TypedDict

from pydantic import JsonValue

from src.configuration import MessageRole


class ToolFunctionDefinition(TypedDict):
    """Describe a callable tool and the JSON schema of its arguments."""

    name: str
    description: str
    parameters: dict[str, JsonValue]


class ToolDefinition(TypedDict):
    """Declare a tool in LiteLLM's request format; no conversion is needed."""

    type: Literal["function"]
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


class ChatTool(TypedDict):
    """Pair a model-facing definition with the Python function to call."""

    definition: ToolDefinition
    handler: Callable[[dict[str, JsonValue]], dict[str, JsonValue]]
