"""
LLM Provider Abstraction layer supporting Ollama, Mock/Deterministic, and Cloud providers.
"""
from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import requests

from support_agent.config import OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_URL
from support_agent.models.schemas import AgentActionType, AgentDecision


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def select_action(self, state_dict: Dict[str, Any], available_tools: List[str]) -> AgentDecision:
        """Decide the next action in the agent loop."""
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL, timeout: int = OLLAMA_TIMEOUT):
        self.url = url
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
        }
        resp = requests.post(self.url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()

    def select_action(self, state_dict: Dict[str, Any], available_tools: List[str]) -> AgentDecision:
        prompt = (
            f"Current user message: {state_dict.get('current_message')}\n"
            f"Intent: {state_dict.get('intent')}\n"
            f"Available tools: {available_tools}\n"
            "Select action in JSON: {\"action\": \"tool\"|\"retrieve\"|\"answer\"|\"ask_clarification\"|\"escalate\", \"tool_name\": str|null, \"tool_args\": dict, \"reason\": str, \"confidence\": float}"
        )
        try:
            raw = self.generate(prompt)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return AgentDecision(**parsed)
        except Exception:
            pass
        # Fall back to deterministic routing if Ollama JSON parsing fails
        return MockDeterministicProvider().select_action(state_dict, available_tools)


class MockDeterministicProvider(LLMProvider):
    """
    Intelligent, grounded, deterministic agent provider.
    Ensures 100% reliable execution for offline demos, CI/CD, and benchmark testing.
    """
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        p_low = prompt.lower()
        if "summary" in p_low:
            return "Customer inquiry regarding support operations and verified status details."
        return "I have verified your request against our customer records and documentation."

    def select_action(self, state_dict: Dict[str, Any], available_tools: List[str]) -> AgentDecision:
        msg = state_dict.get("current_message", "").strip()
        lower = msg.lower()
        step = state_dict.get("current_step", 0)
        tool_results = state_dict.get("tool_results", [])
        tools_executed = [tr.get("tool_name") if isinstance(tr, dict) else tr.tool_name for tr in tool_results]

        # 1. Human Escalation Requests
        clean_msg = re.sub(r"supportagent", "", lower, flags=re.IGNORECASE)
        human_triggers = [r"\bhuman\b", r"\btalk to human\b", r"\bhuman agent\b", r"\bconnect me to a human\b", r"\bsupervisor\b", r"\brepresentative\b", r"\blawyer\b", r"\blegal\b"]
        if any(re.search(pat, clean_msg) for pat in human_triggers):
            if "escalate_to_human" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="escalate_to_human",
                    tool_args={"reason": f"Customer requested human handoff: '{msg}'", "priority": "High"},
                    reason="Customer explicitly requested human intervention.",
                    confidence=0.98,
                )
            return AgentDecision(
                action=AgentActionType.ANSWER,
                reason="Handoff ticket created, now returning final human handoff guidance.",
                confidence=0.95,
            )

        # 2. Extract potential Order ID (ORD-XXXX)
        order_id_match = re.search(r"\bORD-\d+\b", msg.upper())
        order_id = order_id_match.group(0) if order_id_match else None

        # 3. Duplicate Charge / Refund Multi-Step Workflow
        if "charged twice" in lower or "duplicate" in lower:
            if not order_id:
                # Missing order ID - ask clarification
                return AgentDecision(
                    action=AgentActionType.ASK_CLARIFICATION,
                    reason="Duplicate charge reported but no Order ID (e.g. ORD-1024) was provided.",
                    confidence=0.92,
                )

            # Step 1: get_order_details
            if "get_order_details" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="get_order_details",
                    tool_args={"order_id": order_id},
                    reason=f"Step 1: Fetch order details for {order_id} to verify customer purchase.",
                    confidence=0.96,
                )
            # Step 2: get_payment_status
            if "get_payment_status" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="get_payment_status",
                    tool_args={"order_id": order_id},
                    reason=f"Step 2: Inspect payment gateway records for duplicate charges on {order_id}.",
                    confidence=0.96,
                )
            # Step 3: check_refund_eligibility
            if "check_refund_eligibility" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="check_refund_eligibility",
                    tool_args={"order_id": order_id},
                    reason="Step 3: Confirm refund eligibility under billing policy.",
                    confidence=0.95,
                )
            # Step 4: create_refund_request
            if "create_refund_request" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="create_refund_request",
                    tool_args={"order_id": order_id, "reason": "Duplicate payment detected on gateway"},
                    reason="Step 4: Execute sensitive refund request for verified duplicate deduction.",
                    confidence=0.97,
                )
            # Step 5: create_support_ticket if not yet created
            if "create_support_ticket" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="create_support_ticket",
                    tool_args={
                        "topic": f"Duplicate Charge Refund - {order_id}",
                        "priority": "High",
                        "intent": "Billing & Refund",
                        "issue_details": f"Processed duplicate charge refund for {order_id}. Human finance review queued.",
                    },
                    reason="Step 5: Create support ticket for tracking and human follow-up.",
                    confidence=0.94,
                )
            # Step 6: Final grounded answer
            return AgentDecision(
                action=AgentActionType.ANSWER,
                reason="All workflow steps completed. Delivering grounded refund response.",
                confidence=0.98,
            )

        # 5. Order Lookup for any message mentioning an Order ID
        if order_id:
            if "get_order_details" not in tools_executed:
                return AgentDecision(
                    action=AgentActionType.TOOL,
                    tool_name="get_order_details",
                    tool_args={"order_id": order_id},
                    reason=f"Lookup live order details and tracking for {order_id}.",
                    confidence=0.96,
                )
            if "refund" in lower:
                if "check_refund_eligibility" not in tools_executed:
                    return AgentDecision(
                        action=AgentActionType.TOOL,
                        tool_name="check_refund_eligibility",
                        tool_args={"order_id": order_id},
                        reason="Check return window and eligibility for order.",
                        confidence=0.95,
                    )
            return AgentDecision(
                action=AgentActionType.ANSWER,
                reason="Order tracking data retrieved. Providing response.",
                confidence=0.95,
            )

        # 6. General Policy / Knowledge Inquiry (RAG)
        rag_triggers = [
            "policy", "how does", "what is", "return policy", "refund policy", "shipping", "deliver",
            "payment method", "tax", "invoice", "gift card", "software", "bank", "debited",
            "failed", "deduction", "refundable", "when will", "days does"
        ]
        if any(w in lower for w in rag_triggers):
            if "retrieved_documents" not in state_dict or not state_dict.get("retrieved_documents"):
                return AgentDecision(
                    action=AgentActionType.RETRIEVE,
                    reason="Question requires knowledge base policy retrieval.",
                    confidence=0.92,
                )
            return AgentDecision(
                action=AgentActionType.ANSWER,
                reason="Knowledge base chunks retrieved. Generating grounded answer.",
                confidence=0.94,
            )

        # 7. Missing Order ID inquiry
        if any(w in lower for w in ["my order", "my purchase", "last order", "my package"]) and not order_id:
            return AgentDecision(
                action=AgentActionType.ASK_CLARIFICATION,
                reason="Customer mentioned an order but omitted the Order ID (e.g., ORD-1001).",
                confidence=0.90,
            )

        # 8. Default Direct Conversational Response
        return AgentDecision(
            action=AgentActionType.ANSWER,
            reason="General customer query addressed directly.",
            confidence=0.88,
        )


def get_llm_provider(preferred: Optional[str] = None) -> LLMProvider:
    choice = (preferred or os.getenv("LLM_PROVIDER", "mock")).lower()
    if choice == "ollama":
        try:
            # Ping Ollama
            requests.get("http://localhost:11434/api/tags", timeout=1.0)
            return OllamaProvider()
        except Exception:
            # Graceful fallback to mock deterministic
            return MockDeterministicProvider()
    return MockDeterministicProvider()
