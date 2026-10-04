"""Resolve human location descriptions into geographic pitch-search bounds.

This adapter reads Nominatim's address search API and validates its response.
It owns geographic bounds, while the search module owns Overpass retrieval
and public error formatting. HTTP and validation failures propagate to it."""
import httpx

from typing import cast
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict

from src.configuration.constants import constants


class NominatimLocationResponse(BaseModel):
    """Validate the geographic fields needed from a Nominatim match."""

    model_config: ConfigDict = ConfigDict(extra="ignore")
    display_name: str
    boundingbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class ResolvedPitchLocation:
    """Own a resolved place name and its geographic extent."""

    display_name: str
    south: float
    north: float
    west: float
    east: float


def resolve_pitch_search_location(
    neighborhood: str, city: str,
) -> ResolvedPitchLocation | None:
    """Resolve a place description, returning None for an empty search."""
    response: httpx.Response = httpx.get(
        constants.pitches.NOMINATIM.value,
        params={"q": f"{neighborhood}, {city}", "format": "jsonv2",
                "layer": "address", "limit": 1},
        headers={"User-Agent": constants.pitches.USER_AGENT.value},
        timeout=15.0,
    )
    response.raise_for_status()
    payload: object = cast(object, response.json())
    if not isinstance(payload, list):
        raise ValueError("Invalid geocoding results list.")
    if not payload:
        return None
    match: NominatimLocationResponse = NominatimLocationResponse.model_validate(payload[0])
    south: float
    north: float
    west: float
    east: float
    south, north, west, east = match.boundingbox
    if not match.display_name.strip() or not (
        -90 <= south <= north <= 90 and -180 <= west <= east <= 180
    ):
        raise ValueError("Invalid geocoding bounds or place name.")
    return ResolvedPitchLocation(match.display_name, south, north, west, east)
