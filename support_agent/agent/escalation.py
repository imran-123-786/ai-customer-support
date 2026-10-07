"""
Escalation Engine and Human Handoff Summary Generator.
Creates persistent escalation tickets and structured human-assist briefings.
"""
from __future__ import annotations

import random
import re
from typing import Optional
from support_agent.database.repository import repo
from support_agent.models.schemas import (
    AgentState,
    EscalationDecision,
    HandoffSummary,
)


class EscalationEngine:
    def __init__(self):
        pass

    def evaluate_escalation(self, state: AgentState) -> EscalationDecision:
        msg = state.current_message.lower()

        # 1. Explicit human request
        # Avoid false matching 'SupportAgent' when user says 'Hello SupportAgent'
        clean_msg = re.sub(r"supportagent", "", msg, flags=re.IGNORECASE)
        human_triggers = [r"\bhuman\b", r"\btalk to a person\b", r"\bhuman agent\b", r"\bconnect me\b", r"\brepresentative\b", r"\boperator\b", r"\bsupervisor\b"]
        if any(re.search(pat, clean_msg) for pat in human_triggers):
            return EscalationDecision(
                escalate=True,
                reason="Customer explicitly requested human agent assistance.",
                priority="High" if state.emotion in ("angry", "frustrated") else "Medium",
            )

        # 2. Critical security / fraud / legal threat
        if any(k in msg for k in ["fraud", "compromised", "hacked", "stolen", "lawyer", "legal", "sue", "lawsuit"]):
            return EscalationDecision(
                escalate=True,
                reason="High-risk trigger detected: suspected fraud, account compromise, or legal threat.",
                priority="Critical",
            )

        # 3. Exceeded maximum agent loop steps
        if state.current_step >= state.max_steps:
            return EscalationDecision(
                escalate=True,
                reason=f"Agent exceeded maximum iteration limit ({state.max_steps} steps) without completing resolution.",
                priority="High",
            )

        # 4. Tool failures on sensitive transactions
        for tr in state.tool_results:
            if not tr.success:
                return EscalationDecision(
                    escalate=True,
                    reason=f"Automated tool execution failure in `{tr.tool_name}`: {tr.error_message}",
                    priority="High",
                )

        # 5. Severe sentiment with repeat struggle
        if state.emotion == "angry" or (state.emotion == "frustrated" and any(k in msg for k in ["again", "days", "hours"])):
            return EscalationDecision(
                escalate=True,
                reason="Customer expressed severe frustration or reported a recurring unresolved problem.",
                priority="High",
            )

        return EscalationDecision(escalate=False, reason=None, priority=state.priority)

    def generate_handoff_summary(self, state: AgentState, reason: str) -> HandoffSummary:
        # Collate attempted actions
        actions = []
        for tc in state.tool_calls:
            actions.append(f"Executed tool `{tc.tool_name}` with args {tc.tool_args}")
        if state.retrieved_documents:
            actions.append(f"Retrieved {len(state.retrieved_documents)} knowledge base policy documents")
        if not actions:
            actions.append("Direct customer dialogue triage")

        # Determine recommended human action
        rec = "Inspect customer inquiry details and follow up directly."
        if "duplicate" in state.current_message.lower():
            rec = "Verify payment gateway transaction records, authorize refund release, and notify customer."
        elif "refund" in state.current_message.lower():
            rec = "Inspect order return logistics and confirm refund eligibility."
        elif "fraud" in state.current_message.lower() or "hacked" in state.current_message.lower():
            rec = "Freeze account credentials immediately, initiate identity re-verification, and contact security team."
        elif "human" in state.current_message.lower():
            rec = "Take over live conversation and address customer questions."

        return HandoffSummary(
            issue=state.current_message[:120],
            priority=state.priority,
            customer_sentiment=state.emotion.title(),
            actions_attempted=actions,
            recommended_action=rec,
        )

    def trigger_escalation(self, state: AgentState, reason: str, priority: str = "High") -> str:
        ticket_id = f"TICK-{random.randint(8000, 9999)}"
        handoff = self.generate_handoff_summary(state, reason)

        handoff_text = (
            f"=== HUMAN HANDOFF BRIEFING ===\n"
            f"Issue: {handoff.issue}\n"
            f"Priority: {handoff.priority}\n"
            f"Customer Sentiment: {handoff.customer_sentiment}\n"
            f"Actions Attempted:\n" + "\n".join([f" - {a}" for a in handoff.actions_attempted]) + "\n"
            f"Recommended Next Action: {handoff.recommended_action}\n"
        )

        repo.create_ticket(
            ticket_id=ticket_id,
            user_id=state.user_id,
            customer_id=state.customer_id,
            topic=state.current_message[:70],
            intent=state.intent,
            priority=priority,
            status="Open",
            escalated=1,
            escalation_reason=reason,
            handoff_summary=handoff_text,
            assigned_to="tier_2_human_agent",
        )

        state.escalation_required = True
        state.escalation_reason = reason
        state.handoff_summary = handoff_text
        return ticket_id


escalation_engine = EscalationEngine()
