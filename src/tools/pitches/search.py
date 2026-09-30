"""Declare the find_nearby_pitches tool for model discovery.

This module owns the neighborhood search schema and a placeholder function.
It makes no external requests and does not access browser location."""

from typing import TYPE_CHECKING

from pydantic import JsonValue

from src.application.models import ToolDefinition

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "find_nearby_pitches",
        "description": "Find soccer pitches near a neighborhood. Ask the user for their neighborhood if missing, and their city if needed to disambiguate. Do not claim booking availability.",
        "parameters": {
            "type": "object",
            "properties": {
                "neighborhood": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Neighborhood supplied by the user."
                },
                "city": {
                    "type": "string",
                    "minLength": 1,
                    "description": "City containing the neighborhood, when needed to disambiguate."
                }
            },
            "required": ["neighborhood"],
            "additionalProperties": False
        }
    }
}


def find_nearby_pitches(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Return a placeholder result without searching for pitches.

    Example: {"neighborhood": "Harlem"} -> {"ok": False, "error": "Not implemented"}.
    """
    # TODO: Search for pitches near the supplied neighborhood.
    return {"ok": False, "error": "Not implemented"}
