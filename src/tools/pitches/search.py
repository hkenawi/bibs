"""Find soccer pitches within named OpenStreetMap areas.

This tool queries the public Overpass API and returns up to three
mapped pitches. It does not rank distances or mutate session state.
"""

from json import dumps
from typing import TYPE_CHECKING, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from src.application.models import ToolDefinition
from src.application.errors import create_error_result, describe_validation_failure
from src.configuration.constants import constants
from src.application.errors import classify_external_failure

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession


class PitchSearchInput(BaseModel):
    """Validate the named areas supplied through chat."""

    model_config: ConfigDict = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    neighborhood: str = Field(min_length=1)
    city: str = Field(min_length=1)


definition = {
    "type": "function",
    "function": {
        "name": "find_nearby_pitches",
        "description": (
            "Find up to three soccer pitches in a named neighborhood "
            "and city. Ask for missing location details. Results are "
            "not ranked by distance. Show the returned map links and "
            "credit OpenStreetMap contributors."
        ),
        "parameters": cast(
            dict[str, JsonValue],
            PitchSearchInput.model_json_schema(),
        ),
    },
}


def find_nearby_pitches(
    arguments: dict[str, JsonValue],
    session: "ConversationSession",
) -> dict[str, JsonValue]:
    """Return up to three mapped soccer pitches without changing the session."""

    try:
        location = PitchSearchInput.model_validate(arguments)
    except ValidationError as error:
        return describe_validation_failure(error)

    query = f"""
        [out:json][timeout:20];
        area["boundary"="administrative"]
            ["name"={dumps(location.city)}]->.city;
        area["name"={dumps(location.neighborhood)}]->.neighborhood;
        nwr(area.city)(area.neighborhood)
            ["leisure"="pitch"]["sport"="soccer"];
        out tags 3;
    """

    try:
        response = httpx.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "bibs/0.1"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        return classify_external_failure(error)

    if not isinstance(payload, dict) or payload.get("remark"):
        return create_error_result(constants.errors.INVALID_RESPONSE, "Pitch search returned an invalid response.", "Try another area or try again later.")

    elements = payload.get("elements")
    if not isinstance(elements, list):
        return create_error_result(constants.errors.INVALID_RESPONSE, "Pitch search returned no results list.", "Try again later.")

    pitches = []
    for element in elements:
        if not isinstance(element, dict):
            continue

        element_type = element.get("type")
        element_id = element.get("id")
        tags = element.get("tags", {})

        if (
            element_type not in ("node", "way", "relation")
            or type(element_id) is not int
            or not isinstance(tags, dict)
        ):
            continue

        name = tags.get("name")
        pitches.append({
            "name": name if isinstance(name, str) and name else "Unnamed soccer pitch",
            "map_url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
        })

        if len(pitches) == 3:
            break

    return {
        "ok": True,
        "pitches": pitches,
        "message": (
            "Found mapped soccer pitches."
            if pitches
            else "No matching pitches found. Try another neighborhood or district."
        ),
        "attribution": "© OpenStreetMap contributors",
    }
