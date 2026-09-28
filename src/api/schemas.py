"""Validate browser requests and serialize the stable chat HTTP contract.

These Pydantic models belong to the transport boundary, independently of provider
payloads. Strict inputs reject accidental coercion and unexpected fields."""

from pydantic import BaseModel, ConfigDict, Field

from src.application.models import ToolRecord


class ChatRequest(BaseModel):
    model_config: ConfigDict = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = Field(default=None, min_length=1)


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: tuple[ToolRecord, ...] = ()
