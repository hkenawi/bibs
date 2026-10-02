"""Run the bibs agent loop for one user message.

The caller supplies history containing the latest user message and manages
session storage. This function appends assistant messages and tool results."""

from json import dumps
from logging import getLogger, Logger
from typing import cast

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
from src.application.errors import create_error_result, classify_external_failure
from src.tools.registry import TOOLS, run_tool
from src.tools.teams.models import RosterPlayer

logger: Logger = getLogger(__name__)


def run_agent(
    messages: list[ChatMessage],
    session: ConversationSession,
    tools: dict[str, ChatTool] | None = None,
    max_tool_rounds: int = constants.max_tool_rounds,
) -> tuple[str, list[ToolRecord]]:
    """Run a turn while preserving completed results if later work fails."""
    tool: ChatTool
    definitions: tuple[ToolDefinition, ...] = (
        TOOLS
        if tools is None
        else tuple(tool["definition"] for tool in tools.values())
    )
    records: list[ToolRecord] = []
    rounds: int = 0

    while True:
        try:
            reply: ChatMessage = generate_response(tuple(messages), definitions)
        except Exception as error:
            logger.warning("Model request failed: %s", type(error).__name__)
            failure: dict[str, JsonValue] = classify_external_failure(error)
            details: dict[str, JsonValue] = cast(dict[str, JsonValue], failure["error"])
            response: str = f"{details['message']} {details['suggested_action']}"
            successful: list[str] = [record.name for record in records if record.result.get("ok") is True]
            if successful:
                response = "Completed: " + ", ".join(successful) + ". Any saved roster or team changes are preserved. " + response
            messages.append(ChatMessage(constants.roles.ASSISTANT, response))
            return response, records

        if reply.tool_calls and rounds >= max_tool_rounds:
            response = "The tool round limit was reached. Completed results are preserved. Ask to retry only the unfinished operation."
            messages.append(ChatMessage(constants.roles.ASSISTANT, response))
            return response, records

        messages.append(reply)

        if not reply.tool_calls:
            return reply.content, records

        call: ToolRequest
        for call in reply.tool_calls:
            result: dict[str, JsonValue]
            previous_state: tuple[tuple[RosterPlayer, ...], tuple[RosterPlayer, ...], tuple[RosterPlayer, ...], bool] = (session.roster, session.home, session.away, session.dedicated_goalkeepers)
            try:
                if call.invalid_arguments:
                    result = create_error_result(constants.errors.INVALID_INPUT,
                        "Tool arguments must be a valid JSON object.", "Correct the arguments and call the tool again.")
                elif tools is None:
                    result = run_tool(call.name, call.arguments, session)
                elif call.name in tools:
                    result = tools[call.name]["handler"](call.arguments)
                else:
                    result = create_error_result(constants.errors.UNKNOWN_TOOL,
                        "This tool is not available.", "Choose a registered tool.")
                if not isinstance(result, dict):
                    raise ValueError("Invalid tool result")
            except Exception as error:
                logger.warning("Tool %s failed: %s", call.name, type(error).__name__)
                result = create_error_result(constants.errors.TOOL_FAILED,
                    "The tool could not complete its operation.", "Try again or change the request.")
            if result.get("ok") is False:
                session.roster, session.home, session.away, session.dedicated_goalkeepers = previous_state

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
