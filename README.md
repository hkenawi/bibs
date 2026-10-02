# bibs

**Fair teams. More football.**

bibs will help organizers split rosters of 10 or more soccer players into fair
teams, preview swaps, revise teams after roster changes, and find pitches near a neighborhood.

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
- `src/tools/`: tool definitions and placeholder execution methods, grouped into teams and pitches.
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
"parameters": ...}}`. The adapter passes these directly to the model; each tool module's
named function (such as `balance_soccer_teams()`) performs the actual work.
`src/tools/__init__.py` pairs each definition with its function using a plain
dictionary containing `definition` and `handler`. Conversation messages remain
application-owned `ChatMessage` objects with a small conversion at the API boundary.
The default application registers four placeholder tools:

| Tool | Planned purpose |
|---|---|
| `balance_soccer_teams` | Create fair teams from the session roster. |
| `compare_team_options` | Preview a cross-team player swap. |
| `rebalance_with_minimal_swaps` | Revise teams after roster changes. |
| `find_nearby_pitches` | Find soccer pitches near a user-provided neighborhood; ask for the city when needed. |

Ask **“What tools do you have access to? Describe their inputs and whether they
are implemented.”** in the local chat. The definitions are sent to Gemini on each
turn. Executing any placeholder returns `{"ok": false, "error": "Not implemented"}`; no
calculation, session mutation, or pitch search occurs. Input schemas describe
the intended contract; argument validation and business logic remain to be built.
Use `create_app(tools=())` to disable all tools or pass a tuple to replace the defaults.

`POST /chat` accepts `message` and an optional `session_id`. Successful responses
contain `response`, `session_id`, and `tool_calls`, including an empty array when
no tool ran. Reusing the session ID retains history; an unknown ID returns HTTP 404
with `SESSION_EXPIRED`. `GET /health` checks the process without calling a model.
Failures return safe, actionable messages and preserve completed tool records.
External requests classify HTTP failures and use 30-second request timeouts.
They execute once, without automatic retries. There is no overall time limit on a chat turn. Unknown tools and invalid arguments are returned to the
model for correction within the existing tool-round limit.

## Current limits and next steps

This is the Phase 1 architectural foundation. The course starter ZIP has not been
inspected, so compatibility with its implementation is unverified. A real Gemini
request and starter-derived workflow remain unverified Phase 1 completion gates.

Sessions disappear on restart. Use one worker. Concurrent changes to the same session are not coordinated.
The browser retains its tab-specific ID across refresh and restores completed
conversation, roster, and team state through `GET /session`. Duplicated tabs start
independent sessions. An expired session offers explicit recovery using the bench
roster. Compare/rebalance tools and clear/reset endpoints remain later work.
The roster is limited to 3–22 players. Requests execute normally without request-ID
tracking, replay protection, or locks. No new dependencies or persistent storage
were introduced.
