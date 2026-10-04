"""Verify agent-loop guardrails independently of HTTP and provider conversion.

A controlled application-level model response isolates the loop's unknown-tool
handling, execution budget, and rollback behavior. End-to-end workflows cover
successful execution through the real provider adapter elsewhere.
"""

from unittest.mock import MagicMock

import pytest
from pydantic import JsonValue

from src.application import service
from src.application.models import ChatMessage, ChatTool, ToolDefinition, ToolRecord, ToolRequest
from src.application.session_db import ConversationSession
from src.configuration.constants import constants
from src.tools.teams.models import RosterPlayer


def test_unknown_tool_returns_a_correctable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    completion: MagicMock = MagicMock(side_effect=[
        ChatMessage(constants.roles.ASSISTANT, "", (ToolRequest("unknown", "missing", {}),)),
        ChatMessage(constants.roles.ASSISTANT, "Please try another tool."),
    ])
    monkeypatch.setattr(service, "generate_response", completion)
    messages: list[ChatMessage] = [ChatMessage(constants.roles.USER, "Try a tool")]
    response: str
    records: list[ToolRecord]
    response, records = service.run_agent(messages, ConversationSession())
    assert records[0].result["error"]["code"] == "UNKNOWN_TOOL"
    assert messages[-2].tool_call_id == "unknown"
    assert response == "Please try another tool."


def test_loop_stops_executing_tools_at_the_round_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    completion: MagicMock = MagicMock(return_value=ChatMessage(
        constants.roles.ASSISTANT, "", (ToolRequest("repeat", "missing", {}),),
    ))
    monkeypatch.setattr(service, "generate_response", completion)
    response: str
    records: list[ToolRecord]
    response, records = service.run_agent(
        [ChatMessage(constants.roles.USER, "Repeat")], ConversationSession(), max_tool_rounds=2,
    )
    assert "limit" in response
    assert len(records) == 2


def test_failed_tool_rolls_back_mutation_and_hides_exception_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session: ConversationSession = ConversationSession(roster=(
        RosterPlayer(player_id="p1", name="Sara", rating=3),
    ))
    original_roster: tuple[RosterPlayer, ...] = session.roster

    def mutate_then_fail(arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Simulate a tool that changes state before raising an exception."""
        session.roster = ()
        raise RuntimeError("private tool details")

    definition: ToolDefinition = {"type": "function", "function": {
        "name": "broken", "description": "Simulate a tool failure.",
        "parameters": {"type": "object"},
    }}
    tools: dict[str, ChatTool] = {"broken": {"definition": definition, "handler": mutate_then_fail}}
    completion: MagicMock = MagicMock(side_effect=[
        ChatMessage(constants.roles.ASSISTANT, "", (ToolRequest("broken", "broken", {}),)),
        ChatMessage(constants.roles.ASSISTANT, "Try again."),
    ])
    monkeypatch.setattr(service, "generate_response", completion)
    messages: list[ChatMessage] = [ChatMessage(constants.roles.USER, "Run tool")]
    response: str
    records: list[ToolRecord]
    response, records = service.run_agent(messages, session, tools=tools)
    assert session.roster == original_roster
    assert records[0].result["error"]["code"] == "TOOL_FAILED"
    assert "private tool details" not in str(records) + str(messages)
