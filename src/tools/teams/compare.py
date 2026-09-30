"""Declare the compare_team_options tool for model discovery.

This module owns its API schema and a placeholder function. It does not
perform calculations, change session state, or contact external services.
"""

from typing import TYPE_CHECKING

from pydantic import JsonValue

from src.application.models import ToolDefinition

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "compare_team_options",
        "description": "Preview a swap between one Home player and one Away player in the saved plan without saving it. Use known player IDs; clarify ambiguous players.",
        "parameters": {
            "type": "object",
            "properties": {
                "home_player_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Server-issued ID of a player on Home."
                },
                "away_player_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Server-issued ID of a player on Away."
                }
            },
            "required": [
                "home_player_id",
                "away_player_id"
            ],
            "additionalProperties": False
        }
    }
}


def compare_team_options(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Return a placeholder result without performing any work.

    Example: {} -> {"ok": False, "error": "Not implemented"}.
    """
    # TODO: Implement this tool using the supplied arguments and session context.
    return {"ok": False, "error": "Not implemented"}
