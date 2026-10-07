"""
Unit tests for multi-step autonomous orchestrator.
"""
from support_agent.agent.orchestrator import orchestrator


def test_orchestrator_order_lookup_flow():
    state = orchestrator.run("Where is my order ORD-1001?")
    assert state.finished is True
    assert "Wireless Noise-Cancelling Headphones" in state.final_response
    tool_names = [tc.tool_name for tc in state.tool_calls]
    assert "get_order_details" in tool_names


def test_orchestrator_duplicate_refund_multi_step():
    state = orchestrator.run("I was charged twice for ORD-1024 and I want a refund.")
    assert state.finished is True
    tool_names = [tc.tool_name for tc in state.tool_calls]
    assert "get_order_details" in tool_names
    assert "get_payment_status" in tool_names
    assert "check_refund_eligibility" in tool_names
    assert "create_refund_request" in tool_names
    assert "create_support_ticket" in tool_names
    assert "REF-" in state.final_response


def test_orchestrator_escalation_flow():
    state = orchestrator.run("Please connect me to a human representative.")
    assert state.finished is True
    assert state.escalation_required is True
    assert "escalate_to_human" in [tc.tool_name for tc in state.tool_calls]
    assert "Ticket" in state.final_response
