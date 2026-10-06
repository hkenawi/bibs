"""Define shared constants and protocol vocabulary for bibs.

The application uses this object for message roles, error codes, and its tool
round limit. Values are defined in code without environment loading."""

from enum import StrEnum
from dataclasses import dataclass


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ErrorCode(StrEnum):
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    TOOL_FAILED = "TOOL_FAILED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    INVALID_INPUT = "INVALID_INPUT"
    BAD_REQUEST = "BAD_REQUEST"
    ACCESS_DENIED = "ACCESS_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class GeminiSetting(StrEnum):
    MODEL = "vertex_ai/gemini-3.5-flash-lite"
    LOCATION = "global"
    MODE = "gemini"


class PitchServiceSetting(StrEnum):
    NOMINATIM = "https://nominatim.openstreetmap.org/search"
    OVERPASS = "https://overpass-api.de/api/interpreter"
    USER_AGENT = "bibs/0.1"
    FAILURE_LOG = "%s request failed: %s (status=%s)"


@dataclass(frozen=True)
class Constants:
    roles: type[MessageRole] = MessageRole
    errors: type[ErrorCode] = ErrorCode
    gemini: type[GeminiSetting] = GeminiSetting
    pitches: type[PitchServiceSetting] = PitchServiceSetting
    max_tool_rounds: int = 4
    min_players: int = 3
    max_players: int = 22


constants = Constants()
