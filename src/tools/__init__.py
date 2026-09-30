"""Register tool definitions alongside their named Python functions.

Each entry is a plain dictionary. Definitions go to Gemini; handlers execute
locally when the agent loop receives a matching tool call.
"""

from src.application.models import ChatTool
from src.tools.teams import balance, compare, rebalance
from src.tools.pitches import search


def create_default_tools() -> tuple[ChatTool, ...]:
    """Return the four registered tool definitions and their functions.

    Example entry: {"definition": balance.definition,
                    "handler": balance.balance_soccer_teams}.
    """
    return (
        {"definition": balance.definition, "handler": balance.balance_soccer_teams},
        {"definition": compare.definition, "handler": compare.compare_team_options},
        {"definition": rebalance.definition, "handler": rebalance.rebalance_with_minimal_swaps},
        {"definition": search.definition, "handler": search.find_nearby_pitches},
    )
