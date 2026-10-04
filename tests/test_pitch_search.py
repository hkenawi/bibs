"""Verify location resolution through the public pitch-search tool.

External HTTP calls are replaced at their transport boundary, while input
validation, geographic query construction, and result parsing run normally.
"""

from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import JsonValue

from src.application.session_db import ConversationSession
from src.tools.pitches.search import find_nearby_pitches


def test_pitch_search_uses_resolved_bounds_and_reports_the_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Human location wording resolves before the pitch database is queried."""
    geocoder: MagicMock = MagicMock(return_value=httpx.Response(
        200, json=[{"display_name": "Manhattan, New York City, United States",
                    "boundingbox": ["40.68", "40.88", "-74.05", "-73.90"]}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    ))
    overpass: MagicMock = MagicMock(return_value=httpx.Response(
        200, json={"elements": [{"type": "way", "id": 123,
                                 "tags": {"name": "Soccer Field"}}]},
        request=httpx.Request("POST", "https://overpass-api.de/api/interpreter"),
    ))
    monkeypatch.setattr(httpx, "get", geocoder)
    monkeypatch.setattr(httpx, "post", overpass)

    result: dict[str, JsonValue] = find_nearby_pitches(
        {"neighborhood": "Manhattan", "city": "NYC"}, ConversationSession(),
    )

    assert geocoder.call_args.kwargs["params"]["q"] == "Manhattan, NYC"
    query: str = overpass.call_args.kwargs["data"]["data"]
    assert "nwr(40.68,-74.05,40.88,-73.9)" in "".join(query.split())
    assert '["sport"~"(^|;)soccer(;|$)"]' in query
    assert result["searched_location"] == "Manhattan, New York City, United States"
    assert result["pitches"] == [{"name": "Soccer Field",
                                  "map_url": "https://www.openstreetmap.org/way/123"}]


@pytest.mark.parametrize(("payload", "expected_code"), [
    ([], "INVALID_INPUT"),
    ({"unexpected": "object"}, "INVALID_RESPONSE"),
    ([{"display_name": "Manhattan", "boundingbox": ["bad"]}], "INVALID_RESPONSE"),
    ([{"display_name": "Manhattan", "boundingbox": ["95", "96", "0", "1"]}], "INVALID_RESPONSE"),
])
def test_unresolved_or_invalid_locations_do_not_search_for_pitches(
    monkeypatch: pytest.MonkeyPatch, payload: JsonValue, expected_code: str,
) -> None:
    """An unusable location remains distinct from a successful empty search."""
    geocoder: MagicMock = MagicMock(return_value=httpx.Response(
        200, json=payload,
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    ))
    overpass: MagicMock = MagicMock()
    monkeypatch.setattr(httpx, "get", geocoder)
    monkeypatch.setattr(httpx, "post", overpass)
    result: dict[str, JsonValue] = find_nearby_pitches(
        {"neighborhood": "Manhattan", "city": "NYC"}, ConversationSession(),
    )
    assert result["ok"] is False
    assert result["error"]["code"] == expected_code
    overpass.assert_not_called()


@pytest.mark.parametrize("service", ["Nominatim", "Overpass"])
def test_pitch_failures_identify_the_service_in_server_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, service: str,
) -> None:
    """Upstream failure diagnostics identify the stage without leaking bodies."""
    failure: httpx.HTTPStatusError = httpx.HTTPStatusError(
        "private upstream details", request=httpx.Request("GET", "https://example.org"),
        response=httpx.Response(503),
    )
    geocoder: MagicMock = MagicMock(return_value=httpx.Response(
        200, json=[{"display_name": "Harlem", "boundingbox": ["40.8", "40.82", "-73.96", "-73.93"]}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    ))
    overpass: MagicMock = MagicMock(side_effect=failure)
    if service == "Nominatim":
        geocoder.side_effect = failure
    monkeypatch.setattr(httpx, "get", geocoder)
    monkeypatch.setattr(httpx, "post", overpass)
    result: dict[str, JsonValue] = find_nearby_pitches(
        {"neighborhood": "Harlem", "city": "New York"}, ConversationSession(),
    )
    assert result["ok"] is False
    assert f"{service} request failed: HTTPStatusError (status=503)" in caplog.text
    assert "private upstream details" not in caplog.text
