"""Bind HTTP routes to the chat application service.

Routes validate transport data and delegate conversation behavior. They contain
no provider calls or soccer calculations and are bound per application instance."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4
from dataclasses import asdict
from typing import cast
from pydantic import JsonValue

from src.api.schemas import ChatRequest, ChatResponse
from src.application.service import run_agent
from src.application.models import ChatMessage, ChatTool, ToolRecord
from src.application.session_db import ConversationSession, CompletedTurn
from src.configuration.constants import constants


def create_router(
    sessions: dict[str, ConversationSession],
    tools: dict[str, ChatTool] | None,
    frontend: Path,
    model_mode: str,
) -> APIRouter:
    router: APIRouter = APIRouter()

    def reject_request(status_code: int, code: str, message: str) -> None:
        raise HTTPException(status_code=status_code, detail={"code": code, "message": message})

    @router.get("/session")
    def get_session(session_id: str) -> dict[str, JsonValue]:
        session: ConversationSession | None = sessions.get(session_id)
        if session is None:
            reject_request(404, constants.errors.SESSION_EXPIRED, "This session has expired. Start again with your bench roster.")
        assert session is not None
        return {"session_id": session_id, "turns": cast(list[JsonValue], [asdict(turn) | {"tool_calls": [asdict(record) for record in turn.tool_calls]} for turn in session.turns]),
            "state": session.completed_state}


    @router.get("/", include_in_schema=False)
    def get_chat_page() -> FileResponse:
        return FileResponse(frontend / "index.html")

    @router.get("/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok", "model_mode": model_mode}

    @router.post("/chat")
    def post_chat(request: ChatRequest) -> ChatResponse:
        session_id: str = request.session_id or uuid4().hex
        if request.session_id is not None and session_id not in sessions:
            reject_request(404, constants.errors.SESSION_EXPIRED, "This session has expired. Start again with your bench roster.")
        session: ConversationSession = sessions.setdefault(session_id, ConversationSession())
        messages: list[ChatMessage] = list(session.messages)
        messages.append(
            ChatMessage(
                role=constants.roles.USER,
                content=request.message,
            )
        )

        response: str
        tool_calls: list[ToolRecord]
        response, tool_calls = run_agent(
            messages=messages,
            session=session,
            tools=tools,
            max_tool_rounds=constants.max_tool_rounds,
        )

        session.messages = tuple(messages)
        session.turns += (CompletedTurn(request.message, response, tuple(tool_calls)),)
        session.completed_state = {
            "roster": [player.model_dump(mode="json") for player in session.roster],
            "home": [player.model_dump(mode="json") for player in session.home],
            "away": [player.model_dump(mode="json") for player in session.away],
            "dedicated_goalkeepers": session.dedicated_goalkeepers,
        }


        return ChatResponse(
            response=response,
            session_id=session_id,
            tool_calls=tuple(tool_calls),
        )

    return router
