"""Balance the current session roster into two soccer teams.

The tool checks valid splits and minimizes the total rating gap.
Successful results replace the saved teams. Invalid requests leave
session state unchanged. No external services are called.
"""

from itertools import combinations
from typing import TYPE_CHECKING

from pydantic import JsonValue, ValidationError

from src.application.models import ToolDefinition
from src.application.errors import create_error_result, describe_validation_failure
from src.configuration.constants import constants
from src.tools.teams.models import BalanceInput, RosterPlayer

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "balance_soccer_teams",
        "description": (
            "Split the saved roster into two soccer teams with nearly "
            "equal sizes and the smallest total skill rating difference. "
            "Requires at least 3 players. Save players using set_roster "
            "first. Request dedicated goalkeepers only when the user "
            "wants a willing goalkeeper on each team."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dedicated_goalkeepers": {
                    "type": "boolean",
                    "description": (
                        "Whether each team needs a willing goalkeeper. "
                        "Omit to keep the session setting."
                    ),
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
}


def balance_soccer_teams(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Calculate, save, and return the best valid split of the roster."""

    settings: BalanceInput
    try:
        settings = BalanceInput.model_validate(arguments)
    except ValidationError as error:
        return describe_validation_failure(error)

    players: tuple[RosterPlayer, ...] = session.roster
    if not constants.min_players <= len(players) <= constants.max_players:
        return create_error_result(constants.errors.INVALID_INPUT,
            "Teams require 3–22 players.", "Add or remove players and save the roster first.")

    dedicated_goalkeepers: bool = (
        session.dedicated_goalkeepers
        if settings.dedicated_goalkeepers is None
        else settings.dedicated_goalkeepers
    )

    if dedicated_goalkeepers and sum(
        player.goalkeeper_willing for player in players
    ) < 2:
        return create_error_result(constants.errors.INVALID_INPUT,
            "Dedicated goalkeepers require two willing players.", "Identify another keeper or disable dedicated goalkeepers.")

    home_size: int = (len(players) + 1) // 2
    total_rating: int = sum(player.rating for player in players)

    best_gap: int | None = None
    best_home: tuple[RosterPlayer, ...] = ()
    best_away: tuple[RosterPlayer, ...] = ()

    home_indices: tuple[int, ...]
    for home_indices in combinations(range(len(players)), home_size):
        home_index_set: set[int] = set(home_indices)

        home: tuple[RosterPlayer, ...] = tuple(
            players[index] for index in home_indices
        )
        away: tuple[RosterPlayer, ...] = tuple(
            player
            for index, player in enumerate(players)
            if index not in home_index_set
        )

        if dedicated_goalkeepers:
            if not any(player.goalkeeper_willing for player in home):
                continue
            if not any(player.goalkeeper_willing for player in away):
                continue

        home_rating: int = sum(player.rating for player in home)
        gap: int = abs(total_rating - 2 * home_rating)

        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_home = home
            best_away = away

        if best_gap == 0:
            break

    if best_gap is None:
        return create_error_result(constants.errors.INVALID_INPUT, "No valid team split was found.", "Check the roster and goalkeeper settings.")

    session.home = best_home
    session.away = best_away
    session.dedicated_goalkeepers = dedicated_goalkeepers

    return {
        "ok": True,
        "home": [player.model_dump(mode="json") for player in best_home],
        "away": [player.model_dump(mode="json") for player in best_away],
        "home_total": sum(player.rating for player in best_home),
        "away_total": sum(player.rating for player in best_away),
        "rating_gap": best_gap,
    }
