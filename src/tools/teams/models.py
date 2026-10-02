"""Define player data used by roster and team tools.

These models validate structured player data extracted from chat.
They do not access the model provider or mutate session state.
"""

from pydantic import BaseModel, ConfigDict, Field
from src.configuration.constants import constants


class PlayerInput(BaseModel):
    """Represent a player supplied through chat before ID assignment."""

    model_config: ConfigDict = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    name: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    goalkeeper_willing: bool = False


class RosterPlayer(PlayerInput):
    """Represent a validated player with a server-assigned identity."""

    player_id: str = Field(min_length=1)


class RosterInput(BaseModel):
    """Validate a complete replacement roster supplied through chat."""

    model_config: ConfigDict = ConfigDict(
        strict=True,
        extra="forbid",
    )

    players: list[PlayerInput] = Field(min_length=constants.min_players, max_length=constants.max_players)


class BalanceInput(BaseModel):
    """Validate optional settings for balancing the saved roster."""

    model_config: ConfigDict = ConfigDict(
        strict=True,
        extra="forbid",
    )

    dedicated_goalkeepers: bool | None = None
