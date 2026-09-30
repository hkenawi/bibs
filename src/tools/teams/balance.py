"""Declare the balance_soccer_teams tool for model discovery.

This module owns its API schema and a placeholder function. It does not
perform calculations, change session state, or contact external services.
"""

from pydantic import JsonValue

from src.application.models import ToolDefinition


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "balance_soccer_teams",
        "description": "Create a fresh split of the current session roster into fair soccer teams. The server supplies the roster; do not invent player or session IDs.",
        "parameters": {
            "type": "object",
            "properties": {
                "dedicated_goalkeepers": {
                    "type": "boolean",
                    "description": "Whether each team needs a willing goalkeeper. Omit to keep the session setting."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    }
}


def balance_soccer_teams(arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Return a placeholder result without performing any work.

    Example: {} -> {"ok": False, "error": "Not implemented"}.
    """
    # TODO: Implement this tool using the supplied arguments and session context.
    return {"ok": False, "error": "Not implemented"}
