"""Define in-memory conversation storage for bibs.

Each application owns a dictionary of sessions. Conversations are lost when
the server restarts. Concurrent updates are not coordinated at this stage."""

from dataclasses import dataclass

from src.application.models import ChatMessage


@dataclass
class ConversationSession:
    messages: tuple[ChatMessage, ...] = ()
