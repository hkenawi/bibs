"""Collect tool schemas and dispatch model-requested calls.

Schemas are sent to the model. Execution stays in Python, where the
current session is supplied explicitly to tools that need stored data.
"""

from collections.abc import Callable

from pydantic import JsonValue

from src.application.models import ToolDefinition
from src.application.session_db import ConversationSession
from src.tools.pitches import search
from src.tools.teams import balance, compare, rebalance, roster


TOOLS: tuple[ToolDefinition, ...] = (
    roster.definition,
    balance.definition,
    compare.definition,
    rebalance.definition,
    search.definition,
)

HANDLERS: dict[
    str,
    Callable[
        [dict[str, JsonValue], ConversationSession],
        dict[str, JsonValue],
    ],
] = {
    roster.definition["function"]["name"]: roster.set_roster,
    balance.definition["function"]["name"]: balance.balance_soccer_teams,
    compare.definition["function"]["name"]: compare.compare_team_options,
    rebalance.definition["function"]["name"]: (
        rebalance.rebalance_with_minimal_swaps
    ),
    search.definition["function"]["name"]: search.find_nearby_pitches,
}


def run_tool(
    name: str,
    arguments: dict[str, JsonValue],
    session: ConversationSession,
) -> dict[str, JsonValue]:
    """Execute the requested tool with the current conversation session."""

    return HANDLERS[name](arguments, session)
