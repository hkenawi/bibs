"""Construct the bibs HTTP application and connect its components.

Each application receives its own session dictionary and tool registry.
This module connects sessions, routes, and frontend assets without starting a server."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes import create_router
from src.application.models import ChatTool
from src.application.session_db import ConversationSession
from src.configuration.constants import constants


def create_app(
    tools: tuple[ChatTool, ...] | None = None,
) -> FastAPI:
    """Build an app with isolated sessions and optional custom tools.

    Omit tools to use the standard registry. Pass an empty tuple to
    disable tools. Construction does not call the model.
    """

    app = FastAPI(title="bibs")

    sessions = {}
    tool_registry = (
        None
        if tools is None
        else {
            tool["definition"]["function"]["name"]: tool
            for tool in tools
        }
    )
    frontend = Path(__file__).resolve().parents[2] / "frontend"

    app.include_router(
        create_router(
            sessions=sessions,
            tools=tool_registry,
            frontend=frontend,
            model_mode=constants.gemini.MODE.value,
        )
    )
    app.mount("/static", StaticFiles(directory=frontend), name="static")

    return app
