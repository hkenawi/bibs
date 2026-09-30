# bibs

**Fair teams. More football.**

bibs will help organizers split rosters of 10 or more soccer players into fair
teams, preview swaps, revise teams after roster changes, and check match weather.

## Local foundation

Requires Python 3.12+ and `uv`.

```sh
uv sync
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for Gemini chat, or `/docs` for the API explorer.
The adapter calls `vertex_ai/gemini-3.5-flash-lite` in the `global` location through
LiteLLM using Google Application Default Credentials. Your Google Cloud project
needs billing, Vertex AI API access, and permission to use the requested model.
No `.env` file or API key is needed. Live model availability and credentials must
be verified in your own project; automated tests mock the provider boundary.

```sh
uv run pytest -q
uv run pytest tests/unit -q
```

The tool round limit is set in `src/configuration/constants.py` as
`constants.max_tool_rounds`. The model and location are exposed through
`constants.gemini`. Environment files are not loaded automatically.

## Architecture

- `app.py`: thin ASGI entry point.
- `src/api/`: application factory, HTTP routes, and request/response schemas.
- `src/application/service.py`: simple bounded agent loop.
- `src/application/models.py`: shared messages, tool records, and model/tool interfaces.
- `src/application/session_db.py`: conversation dataclass and a dictionary of sessions.
- `src/integrations/model.py`: Gemini adapter for messages and tool calls.
- `src/configuration/`: shared constants and protocol enums.
- `frontend/`: basic browser chat, loading/errors, and expandable tool records.
- `tests/unit/`: adapter unit tests with mocked LiteLLM calls.
- `tests/test_chat_*.py`: HTTP and agent-loop integration tests.

`create_app(tools=...)` accepts the available tools. The agent loop imports
`generate_response(messages, tools)` directly from `src/integrations/model.py`.
That function returns an assistant `ChatMessage`. Messages preserve
assistant tool requests and matching tool-result IDs. Tool adapters expose typed
definitions and must validate arguments before performing their operations.
Tool definitions are `ToolDefinition` typed dictionaries, already in LiteLLM's
format: `{"type": "function", "function": {"name": ..., "description": ...,
"parameters": ...}}`. The adapter passes these directly to the model; each tool's
`execute_tool()` method performs the actual work. Conversation messages remain
application-owned `ChatMessage` objects with a small conversion at the API boundary.
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
request and starter-derived workflow remain unverified Phase 1 completion gates.

Sessions disappear on restart. Use one worker. Concurrent updates to the same
session are not coordinated yet and can overwrite history. This initial browser keeps its ID
only while the page remains open; refresh restoration, clear/reset endpoints,
roster management, soccer tools, weather, and the final interface are later phases.
The round limit bounds model/tool cycles; provider timeouts, retries, raw tool JSON
validation, and production hardening belong to the dedicated error-handling phase.
