"""Find soccer pitches within named OpenStreetMap areas.

This tool resolves locations with Nominatim, queries their bounding boxes
through Overpass, and returns up to three mapped pitches. Bounds may include
nearby areas outside a named boundary. It does not rank distances or mutate
session state."""

import httpx

from logging import Logger, getLogger
from typing import TYPE_CHECKING, cast
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationError,
)

from src.application.models import ToolDefinition
from src.configuration.constants import constants
from src.application.errors import classify_external_failure
from src.application.errors import (
    create_error_result,
    describe_validation_failure,
)
from src.tools.pitches.location import (
    ResolvedPitchLocation,
    resolve_pitch_search_location,
)

if TYPE_CHECKING:
    from src.application.session_db import ConversationSession

logger: Logger = getLogger(__name__)


class PitchSearchInput(BaseModel):
    """Validate the named areas supplied through chat."""

    model_config: ConfigDict = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    neighborhood: str = Field(min_length=1)
    city: str = Field(min_length=1)


definition: ToolDefinition = {
    "type": "function",
    "function": {
        "name": "find_nearby_pitches",
        "description": (
            "Find up to three soccer pitches in a named neighborhood "
            "and city. Ask for missing location details. Results are "
            "not ranked by distance. Search uses a bounding box and may "
            "include adjacent areas. Show the resolved searched_location, "
            "the returned map links and "
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
        location: PitchSearchInput = PitchSearchInput.model_validate(arguments)
    except ValidationError as error:
        return describe_validation_failure(error)

    try:
        resolved: ResolvedPitchLocation | None = resolve_pitch_search_location(
            location.neighborhood,
            location.city,
        )
    except (httpx.HTTPError, ValueError) as error:
        logger.warning(
            constants.pitches.FAILURE_LOG.value,
            "Nominatim",
            type(error).__name__,
            (
                error.response.status_code
                if isinstance(error, httpx.HTTPStatusError)
                else None
            ),
        )
        return classify_external_failure(error)

    if resolved is None:
        return create_error_result(
            constants.errors.INVALID_INPUT,
            "Couldn't locate that place.",
            "Try a fuller neighborhood and city name.",
        )

    query: str = f"""
        [out:json][timeout:20];
        nwr({resolved.south},{resolved.west},{resolved.north},{resolved.east})
            ["leisure"="pitch"]["sport"~"(^|;)soccer(;|$)"];
        out tags 3;
    """

    try:
        response: httpx.Response = httpx.post(
            constants.pitches.OVERPASS.value,
            data={"data": query},
            headers={"User-Agent": constants.pitches.USER_AGENT.value},
            timeout=30.0,
        )
        response.raise_for_status()
        payload: object = cast(object, response.json())
    except (httpx.HTTPError, ValueError) as error:
        logger.warning(
            constants.pitches.FAILURE_LOG.value,
            "Overpass",
            type(error).__name__,
            (
                error.response.status_code
                if isinstance(error, httpx.HTTPStatusError)
                else None
            ),
        )
        return classify_external_failure(error)

    if not isinstance(payload, dict) or payload.get("remark"):
        return create_error_result(
            constants.errors.INVALID_RESPONSE,
            "Pitch search returned an invalid response.",
            "Try another area or try again later.",
        )

    elements: object = payload.get("elements")
    if not isinstance(elements, list):
        return create_error_result(
            constants.errors.INVALID_RESPONSE,
            "Pitch search returned no results list.",
            "Try again later.",
        )

    pitches: list[JsonValue] = []
    element: object
    for element in elements:
        if not isinstance(element, dict):
            continue

        element_type: object = element.get("type")
        element_id: object = element.get("id")
        tags: object = element.get("tags", {})

        if (
            element_type not in ("node", "way", "relation")
            or type(element_id) is not int
            or not isinstance(tags, dict)
        ):
            continue

        name: object = tags.get("name")
        pitches.append(
            {
                "name": (
                    name if isinstance(name, str) and name else "Unnamed soccer pitch"
                ),
                "map_url": f"https://www.openstreetmap.org/{element_type}/{element_id}",
            }
        )

        if len(pitches) == 3:
            break

    return {
        "ok": True,
        "searched_location": resolved.display_name,
        "pitches": pitches,
        "message": (
            "Found mapped soccer pitches."
            if pitches
            else "No matching pitches found. Try another neighborhood or district."
        ),
        "attribution": "© OpenStreetMap contributors",
    }
