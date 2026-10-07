"""
Unit tests for EscalationEngine and Human Handoff generation.
"""
from support_agent.agent.escalation import escalation_engine
from support_agent.models.schemas import AgentState


def test_explicit_human_escalation():
    state = AgentState(
        run_id="run-esc-1",
        conversation_id="conv-esc-1",
        current_message="Connect me to a human right now",
    )
    decision = escalation_engine.evaluate_escalation(state)
    assert decision.escalate is True
    assert "human" in decision.reason.lower()


def test_handoff_summary_generation():
    state = AgentState(
        run_id="run-esc-2",
        conversation_id="conv-esc-2",
        current_message="I was charged twice for ORD-1024",
        emotion="frustrated",
        priority="High",
    )
    summary = escalation_engine.generate_handoff_summary(state, reason="Duplicate charge verification")
    assert "ORD-1024" in summary.issue
    assert summary.priority == "High"
    assert "Frustrated" in summary.customer_sentiment
    assert len(summary.recommended_action) > 10
