"""Collect tool schemas and dispatch model-requested calls.

Schemas are sent to the model. Execution stays in Python, where the
current session is supplied explicitly to tools that need stored data.
"""

from collections.abc import Callable

from pydantic import JsonValue

from src.application.models import ToolDefinition
from src.application.session_db import ConversationSession
from src.application.errors import create_error_result
from src.configuration.constants import constants
from src.tools.pitches import search
from src.tools.teams import balance, roster


# TODO: Consider registering the rebalance tool once its behavior is implemented.
# TODO: Consider registering the compare tool once its behavior is implemented.
TOOLS = (
    roster.definition,
    balance.definition,
    search.definition,
)

HANDLERS = {
    roster.definition["function"]["name"]: roster.set_roster,
    balance.definition["function"]["name"]: balance.balance_soccer_teams,
    search.definition["function"]["name"]: search.find_nearby_pitches,
}


def run_tool(
    name: str,
    arguments: dict[str, JsonValue],
    session: ConversationSession,
) -> dict[str, JsonValue]:
    """Execute the requested tool with the current conversation session."""

    if name not in HANDLERS:
        return create_error_result(constants.errors.UNKNOWN_TOOL,
            "This tool is not available.", "Choose a registered tool.")
    return HANDLERS[name](arguments, session)
