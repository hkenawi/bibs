"""Run the bibs agent loop for one user message.

The caller supplies history containing the latest user message and manages
session storage. This function appends assistant messages and tool results."""

from json import dumps

from pydantic import JsonValue

from src.application.models import (
    ChatMessage,
    ChatTool,
    ToolDefinition,
    ToolRecord,
    ToolRequest,
)
from src.configuration.constants import constants
from src.integrations.model import generate_response
from src.application.session_db import ConversationSession
from src.tools.registry import TOOLS, run_tool


def run_agent(
    messages: list[ChatMessage],
    session: ConversationSession,
    tools: dict[str, ChatTool] | None = None,
    max_tool_rounds: int = constants.max_tool_rounds,
) -> tuple[str, list[ToolRecord]]:
    tool: ChatTool
    definitions: tuple[ToolDefinition, ...] = (
        TOOLS
        if tools is None
        else tuple(tool["definition"] for tool in tools.values())
    )
    records: list[ToolRecord] = []
    rounds: int = 0

    while True:
        reply: ChatMessage = generate_response(
            tuple(messages), definitions
        )

        if reply.tool_calls and rounds >= max_tool_rounds:
            return "The tool round limit was reached.", records

        messages.append(reply)

        if not reply.tool_calls:
            return reply.content, records

        call: ToolRequest
        for call in reply.tool_calls:
            result: dict[str, JsonValue]
            if tools is None:
                result = run_tool(call.name, call.arguments, session)
            else:
                result = tools[call.name]["handler"](call.arguments)

            record: ToolRecord = ToolRecord(
                name=call.name,
                args=call.arguments,
                result=result,
            )
            records.append(record)

            messages.append(
                ChatMessage(
                    role=constants.roles.TOOL,
                    content=dumps(record.result),
                    tool_call_id=call.call_id,
                )
            )

        rounds += 1
