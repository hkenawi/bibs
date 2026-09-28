"""Run the bibs agent loop for one user message.

The caller supplies history containing the latest user message and manages
session storage. This function appends assistant messages and tool results."""

from json import dumps

from src.application.models import (
    ChatMessage,
    ChatTool,
    ToolDefinition,
    ToolRecord,
    ToolRequest,
)
from src.configuration import constants
from src.integrations.model import generate_response


def run_agent(
    messages: list[ChatMessage],
    tools: dict[str, ChatTool],
    max_tool_rounds: int = constants.max_tool_rounds,
) -> tuple[str, list[ToolRecord]]:
    definitions: tuple[ToolDefinition, ...] = tuple(
        tool.definition for tool in tools.values()
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
            record: ToolRecord = ToolRecord(
                name=call.name,
                args=call.arguments,
                result=tools[call.name].execute_tool(call.arguments),
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
