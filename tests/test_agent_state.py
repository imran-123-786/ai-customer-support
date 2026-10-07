"""
Unit tests for AgentState and Pydantic schemas.
"""
from support_agent.models.schemas import (
    AgentActionType,
    AgentDecision,
    AgentState,
    FailureCategory,
    PermissionLevel,
    RetrievedDocument,
    ToolCallRecord,
    ToolResultRecord,
)


def test_agent_state_defaults():
    state = AgentState(
        run_id="run-test-01",
        conversation_id="conv-test-01",
        current_message="Where is my order ORD-1001?",
    )
    assert state.run_id == "run-test-01"
    assert state.current_step == 0
    assert state.max_steps == 6
    assert not state.escalation_required
    assert state.failure_category is None
    assert len(state.tool_calls) == 0


def test_agent_decision_schema():
    decision = AgentDecision(
        action=AgentActionType.TOOL,
        tool_name="get_order_details",
        tool_args={"order_id": "ORD-1001"},
        reason="Lookup order tracking",
        confidence=0.95,
    )
    assert decision.action == AgentActionType.TOOL
    assert decision.tool_name == "get_order_details"
    assert decision.tool_args["order_id"] == "ORD-1001"
    assert decision.confidence == 0.95
