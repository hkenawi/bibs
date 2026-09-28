"""Bind HTTP routes to the chat application service.

Routes validate transport data and delegate conversation behavior. They contain
no provider calls or soccer calculations and are bound per application instance."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4

from src.api.schemas import ChatRequest, ChatResponse
from src.application import run_agent
from src.application.models import ChatMessage, ChatTool, ToolRecord
from src.application.session_db import ConversationSession
from src.configuration import constants


def create_router(
    sessions: dict[str, ConversationSession],
    tools: dict[str, ChatTool],
    frontend: Path,
    model_mode: str,
) -> APIRouter:
    router: APIRouter = APIRouter()

    @router.get("/", include_in_schema=False)
    def get_chat_page() -> FileResponse:
        return FileResponse(frontend / "index.html")

    @router.get("/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok", "model_mode": model_mode}

    @router.post("/chat")
    def post_chat(request: ChatRequest) -> ChatResponse:
        session_id: str = request.session_id or uuid4().hex

        if request.session_id is None:
            sessions[session_id] = ConversationSession()
        elif session_id not in sessions:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": constants.errors.SESSION_EXPIRED,
                    "message": (
                        "This session has expired. "
                        "Start a new conversation."
                    ),
                },
            )

        session: ConversationSession = sessions[session_id]
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
            tools=tools,
            max_tool_rounds=constants.max_tool_rounds,
        )

        session.messages = tuple(messages)

        return ChatResponse(
            response=response,
            session_id=session_id,
            tool_calls=tuple(tool_calls),
        )

    return router
