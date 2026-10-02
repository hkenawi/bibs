"""Declare the rebalance_with_minimal_swaps tool for model discovery.

This module owns its API schema and a placeholder function. It does not
perform calculations, change session state, or contact external services.
"""

from typing import TYPE_CHECKING

from pydantic import JsonValue

from src.application.models import ToolDefinition

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


definition = {
    "type": "function",
    "function": {
        "name": "rebalance_with_minimal_swaps",
        "description": "Revise the saved teams after roster additions, removals, or corrections. fewest_changes prioritizes continuity within one total rating point of the best gap; best_balance prioritizes skill balance. Session data is supplied by the server.",
        "parameters": {
            "type": "object",
            "properties": {
                "additions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Display name for the new player."
                            },
                            "rating": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Overall skill; omitted ratings will default to 3."
                            },
                            "goalkeeper_willingness": {
                                "type": "string",
                                "enum": [
                                    "yes",
                                    "no",
                                    "unspecified"
                                ],
                                "description": "Only yes means willing to play goalkeeper."
                            }
                        },
                        "required": [
                            "name"
                        ],
                        "additionalProperties": False
                    },
                    "description": "New players; the server assigns their IDs."
                },
                "removals": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Server-issued ID of a departing player."
                    },
                    "uniqueItems": True
                },
                "updates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "player_id": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Existing server-issued player ID."
                            },
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "description": "Corrected display name."
                            },
                            "rating": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5
                            },
                            "goalkeeper_willingness": {
                                "type": "string",
                                "enum": [
                                    "yes",
                                    "no",
                                    "unspecified"
                                ]
                            }
                        },
                        "required": [
                            "player_id"
                        ],
                        "additionalProperties": False
                    },
                    "description": "Existing player corrections; include at least one changed field per player."
                },
                "priority": {
                    "type": "string",
                    "enum": [
                        "fewest_changes",
                        "best_balance"
                    ],
                    "description": "Choose the optimization priority."
                }
            },
            "required": [
                "priority"
            ],
            "additionalProperties": False
        }
    }
}


def rebalance_with_minimal_swaps(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Return a placeholder result without performing any work.

    Example: {} -> {"ok": False, "error": "Not implemented"}.
    """
    # TODO: Implement this tool using the supplied arguments and session context.
    return {"ok": False, "error": "Not implemented"}
