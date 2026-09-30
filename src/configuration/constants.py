"""Define shared constants and protocol vocabulary for bibs.

The application uses this object for message roles, error codes, and its tool
round limit. Values are defined in code without environment loading."""

from dataclasses import dataclass
from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ErrorCode(StrEnum):
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    TOOL_FAILED = "TOOL_FAILED"
    SESSION_EXPIRED = "SESSION_EXPIRED"


class GeminiSetting(StrEnum):
    MODEL = "vertex_ai/gemini-3.5-flash-lite"
    LOCATION = "global"
    MODE = "gemini"


@dataclass(frozen=True)
class Constants:
    roles: type[MessageRole] = MessageRole
    errors: type[ErrorCode] = ErrorCode
    gemini: type[GeminiSetting] = GeminiSetting
    max_tool_rounds: int = 4


constants: Constants = Constants()
