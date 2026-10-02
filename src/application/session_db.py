"""Define in-memory conversation and roster storage for bibs.

Each application owns its session dictionary. Messages and players are
lost when the server restarts. Completed responses are retained for refresh restoration.
Concurrent changes to the same session are not coordinated.
"""

from dataclasses import dataclass, field
from pydantic import JsonValue

from src.application.models import ChatMessage, ToolRecord
from src.tools.teams.models import RosterPlayer


@dataclass(frozen=True)
class CompletedTurn:
    """Store a completed response for refresh restoration."""

    message: str
    response: str
    tool_calls: tuple[ToolRecord, ...]


@dataclass
class ConversationSession:
    messages: tuple[ChatMessage, ...] = ()
    roster: tuple[RosterPlayer, ...] = ()
    home: tuple[RosterPlayer, ...] = ()
    away: tuple[RosterPlayer, ...] = ()
    dedicated_goalkeepers: bool = False
    turns: tuple[CompletedTurn, ...] = ()
    completed_state: dict[str, JsonValue] = field(default_factory=dict)
