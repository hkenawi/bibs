# bibs

**Fair teams. More football.**

bibs will help organizers split rosters of 10 or more soccer players into fair
teams, preview swaps, revise teams after roster changes, and check match weather.

## Local foundation

Requires Python 3.12+ and `uv`.

```sh
uv sync
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the demo chat, or `/docs` for the API explorer.
The default adapter produces labeled, deterministic demo responses and makes no
external requests. No API key is required. Gemini integration is deferred.

```sh
uv run pytest -q
```

The tool round limit is set in `src/configuration/constants.py` as
`constants.max_tool_rounds`. Environment files are not loaded automatically. Keep credentials in uncommitted
local configuration when a real provider is added.

## Architecture

- `app.py`: thin ASGI entry point.
- `src/api/`: application factory, HTTP routes, and request/response schemas.
- `src/application/service.py`: simple bounded agent loop.
- `src/application/models.py`: shared messages, tool records, and model/tool interfaces.
- `src/application/session_db.py`: conversation dataclass and a dictionary of sessions.
- `src/integrations/model.py`: standalone response function; future Gemini connection.
- `src/configuration/`: shared constants and protocol enums.
- `frontend/`: basic browser chat, loading/errors, and expandable tool records.

`create_app(tools=...)` accepts the available tools. The agent loop imports
`generate_response(messages, tools)` directly from `src/integrations/model.py`.
That function returns an assistant `ChatMessage`; tests temporarily replace it. Messages preserve
assistant tool requests and matching tool-result IDs. Tool adapters expose typed
definitions and must validate arguments before performing their operations.
The default application registers no tools. Contract tests use a test-only tool.

`POST /chat` accepts `message` and an optional `session_id`. Successful responses
contain `response`, `session_id`, and `tool_calls`, including an empty array when
no tool ran. Reusing the session ID retains history; an unknown ID returns HTTP 404
with `SESSION_EXPIRED`. `GET /health` checks the process without calling a model.
Model and tool exceptions currently propagate; custom error handling is deferred
to a dedicated phase. The existing session-not-found response remains in place.

## Current limits and next steps

This is the Phase 1 architectural foundation. The course starter ZIP has not been
inspected, so compatibility with its implementation is unverified. A real Gemini
request and starter-derived workflow remain deferred Phase 1 completion gates.

Sessions disappear on restart. Use one worker. Concurrent updates to the same
session are not coordinated yet and can overwrite history. This initial browser keeps its ID
only while the page remains open; refresh restoration, clear/reset endpoints,
roster management, soccer tools, weather, and the final interface are later phases.
The round limit bounds model/tool cycles; provider timeouts, retries, raw tool JSON
validation, and production hardening belong to the dedicated error-handling phase.
