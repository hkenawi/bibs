"""Define in-memory conversation and roster storage for bibs.

Each application owns its session dictionary. Messages and players are
lost when the server restarts. Concurrent updates are not coordinated.
"""

from dataclasses import dataclass

from src.application.models import ChatMessage
from src.tools.teams.models import RosterPlayer


@dataclass
class ConversationSession:
    messages: tuple[ChatMessage, ...] = ()
    roster: tuple[RosterPlayer, ...] = ()
    home: tuple[RosterPlayer, ...] = ()
    away: tuple[RosterPlayer, ...] = ()
    dedicated_goalkeepers: bool = False
