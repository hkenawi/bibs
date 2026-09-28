"""Construct the bibs HTTP application and connect its components.

Each application receives its own session dictionary and tool registry.
This module connects sessions, routes, and frontend assets without starting a server."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes import create_router
from src.application.models import ChatTool
from src.application.session_db import ConversationSession


def create_app(
    tools: tuple[ChatTool, ...] = (),
) -> FastAPI:
    app: FastAPI = FastAPI(title="bibs")
    sessions: dict[str, ConversationSession] = {}
    tool_registry: dict[str, ChatTool] = {
        tool.definition.name: tool for tool in tools
    }
    frontend: Path = Path(__file__).resolve().parents[2] / "frontend"

    app.include_router(
        create_router(
            sessions=sessions,
            tools=tool_registry,
            frontend=frontend,
            model_mode="demo",
        )
    )
    app.mount("/static", StaticFiles(directory=frontend), name="static")

    return app
