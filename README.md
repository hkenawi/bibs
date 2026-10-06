# bibs

## Table of contents

- [Project description](#project-description)
- [Tools](#tools)
- [Repository layout](#repository-layout)
- [Run locally](#run-locally)
- [Sample queries](#sample-queries)

## Project description

bibs is a conversational soccer organizer that saves rosters of 3–22 players 
with skill ratings from1 to 5, splits them into two teams with nearly equal 
sizes and the smallest totalrating difference, and optionally places a willing 
goalkeeper on each team. It also searches for up to three soccer pitches in a 
named neighborhood and city, returning map links. 

## Tools

- **`set_roster`** — Saves player names, skill ratings, and goalkeeper preferences for the current session.
- **`balance_soccer_teams`** — Splits the saved roster into balanced teams, optionally assigning a willing goalkeeper to each.
- **`find_nearby_pitches`** — Searches a neighborhood and city for up to three mapped soccer pitches and returns their OpenStreetMap links.

## Repository layout

```text
bibs/
├── app.py                  # ASGI entry point
├── src/                    # Python application modules
│   ├── api/                # Application setup, HTTP routes, and schemas
│   ├── application/        # Agent loop, conversation state, and errors
│   ├── configuration/      # Shared constants and model settings
│   ├── integrations/       # Gemini adapter through LiteLLM
│   └── tools/              # Tool schemas and dispatch
│       ├── teams/          # Player models, roster saving, and team balancing
│       └── pitches/        # OpenStreetMap pitch search
├── frontend/               # Browser chat HTML, CSS, and JavaScript
├── tests/
│   ├── unit/               # Domain logic and agent-loop guardrails
│   ├── integration/        # External-service adapters, with controlled responses
│   └── e2e/                # Complete backend flows through the HTTP API
├── pyproject.toml          # Python dependencies and project configuration
├── uv.lock                 # Locked dependency versions
└── submission.json         # Assignment submission metadata
```

## Run locally

Prerequisites: Python 3.12+, `uv`, and the Google Cloud CLI (`gcloud`). 
Use a Google Cloud project with the Vertex AI API enabled, and credentials 
with permission to access the configured Gemini model.

From the repository root:

```sh
uv sync
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
uv run uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Replace `YOUR_PROJECT_ID` with your Google Cloud project ID. Open the
[chat interface](http://127.0.0.1:8000) or the
[API explorer](http://127.0.0.1:8000/docs).

The model is configured as `vertex_ai/gemini-3.5-flash-lite` in the `global`
location in `src/configuration/constants.py`. Authentication uses Google
Application Default Credentials; no API key or `.env` file is required, and
`.env` files are not loaded automatically. Run a single server worker because
sessions are stored in memory.

## Sample queries

Each query can be pasted into a fresh chat session.

1. **Balance a roster:** “Save these 10 players, with skill ratings out of 5:
   Alex 5, Ben 4, Casey 3, Dana 2, Eli 1, Frankie 5, Grace 4, Harper 3, Ivan 2,
   and Jules 1. Split them into two balanced teams and show each team's total
   rating.”
2. **Balance with goalkeepers:** “Save these players, with skill ratings out of
   5: Alex 5 (willing goalkeeper), Ben 4, Casey 3, Dana 2, Eli 1, Frankie 5
   (willing goalkeeper), Grace 4, Harper 3, Ivan 2, and Jules 1. Create balanced
   teams with a willing goalkeeper on each team.”
3. **Find pitches:** “Find up to three soccer pitches in Harlem, New York City.
   Show their map links.”
