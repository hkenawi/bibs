"""Validate and save the complete player roster for one session.

The tool accepts structured player data extracted from chat. Validation
finishes before session mutation. Player IDs are generated locally.
"""

from typing import TYPE_CHECKING, cast
from uuid import uuid4

from pydantic import JsonValue, ValidationError

from src.application.models import ToolDefinition
from src.tools.teams.models import PlayerInput, RosterInput, RosterPlayer

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "set_roster",
        "description": (
            "Save the complete player list from chat. Each player needs "
            "a name and an integer skill rating from 1 to 5. Ask for "
            "missing ratings; do not invent them. GK means willing to "
            "play goalkeeper. For corrections, send the complete updated "
            "list, including unchanged players. Show the saved roster."
        ),
        "parameters": cast(
            dict[str, JsonValue],
            RosterInput.model_json_schema(),
        ),
    },
}


def set_roster(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Replace the session roster only after validating every player."""

    roster_input: RosterInput
    try:
        roster_input = RosterInput.model_validate(arguments)
    except ValidationError as error:
        return {"ok": False, "error": str(error)}

    normalized_names: list[str] = [
        player.name.casefold() for player in roster_input.players
    ]
    if len(normalized_names) != len(set(normalized_names)):
        return {
            "ok": False,
            "error": (
                "Players need distinct names. Add a surname or initial "
                "to distinguish players with the same name."
            ),
        }

    existing_ids: dict[str, str] = {
        player.name.casefold(): player.player_id
        for player in session.roster
    }
    saved_players: list[RosterPlayer] = []
    player: PlayerInput
    for player in roster_input.players:
        player_id: str | None = existing_ids.get(player.name.casefold())
        saved_players.append(
            RosterPlayer(
                player_id=player_id if player_id is not None else uuid4().hex,
                name=player.name,
                rating=player.rating,
                goalkeeper_willing=player.goalkeeper_willing,
            )
        )

    session.roster = tuple(saved_players)
    session.home = ()
    session.away = ()

    return {
        "ok": True,
        "players": [
            player.model_dump(mode="json") for player in session.roster
        ],
    }
