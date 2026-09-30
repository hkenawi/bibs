"""Verify validation of player data extracted from chat.

Tests exercise the public player models without provider calls,
session storage, or team calculations.
"""

import pytest
from pydantic import ValidationError

from src.tools.teams.models import PlayerInput, RosterPlayer


def test_validate_player_and_trim_name() -> None:
    player: PlayerInput = PlayerInput(name=" Ahmed ", rating=4)

    assert player.name == "Ahmed"
    assert player.rating == 4
    assert player.goalkeeper_willing is False


def test_accept_willing_goalkeeper() -> None:
    player: PlayerInput = PlayerInput(
        name="Sara",
        rating=3,
        goalkeeper_willing=True,
    )

    assert player.goalkeeper_willing is True


@pytest.mark.parametrize("rating", [0, 6, 2.5, "4", True, None])
def test_reject_invalid_rating(
    rating: int | float | str | bool | None,
) -> None:
    with pytest.raises(ValidationError):
        PlayerInput.model_validate(
            {"name": "Ahmed", "rating": rating}
        )


def test_require_rating() -> None:
    with pytest.raises(ValidationError):
        PlayerInput.model_validate({"name": "Ahmed"})


def test_reject_blank_name() -> None:
    with pytest.raises(ValidationError):
        PlayerInput(name="   ", rating=3)


def test_preserve_server_assigned_id() -> None:
    player: RosterPlayer = RosterPlayer(
        player_id="p1",
        name="Ahmed",
        rating=4,
    )

    assert player.player_id == "p1"
    assert player.name == "Ahmed"
