"""
Short-term conversation memory and rolling summarization.
Maintains recent message window and compresses older messages into a coherent summary.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from support_agent.config import RECENT_MESSAGES_LIMIT


class ConversationMemory:
    def __init__(self, recent_limit: int = RECENT_MESSAGES_LIMIT):
        self.recent_limit = recent_limit
        self.messages: List[Dict[str, Any]] = []
        self.summary: str = ""

    def add_message(self, role: str, text: str, **kwargs) -> None:
        self.messages.append({"role": role, "text": text, **kwargs})
        if len(self.messages) > self.recent_limit * 2:
            self.compress()

    def get_recent_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        lim = limit or self.recent_limit
        return self.messages[-lim:] if len(self.messages) > lim else list(self.messages)

    def get_summary(self) -> str:
        return self.summary

    def compress(self) -> str:
        """
        Compress older messages into a structured summary.
        Preserves unresolved issues, order numbers, preferences, and action items.
        """
        if len(self.messages) <= self.recent_limit:
            return self.summary

        old_messages = self.messages[:-self.recent_limit]
        extracted_facts: List[str] = []

        for msg in old_messages:
            text = msg.get("text", "")
            # Look for order numbers
            for word in text.split():
                if word.upper().startswith("ORD-") or word.upper().startswith("TICK-") or word.upper().startswith("PAY-"):
                    clean_id = word.strip(".,;:!?()[]")
                    if clean_id not in extracted_facts:
                        extracted_facts.append(f"Identified entity: {clean_id}")

            # Capture key user concerns
            if msg.get("role") == "user":
                lower = text.lower()
                if "refund" in lower:
                    extracted_facts.append("Customer requested refund assistance.")
                if "duplicate" in lower or "twice" in lower:
                    extracted_facts.append("Customer reported duplicate billing on payment gateway.")
                if "track" in lower or "where is" in lower:
                    extracted_facts.append("Customer requested order tracking status.")
                if "hindi" in lower or "bengali" in lower:
                    extracted_facts.append("Customer expressed language preference.")

        # Deduplicate facts
        unique_facts = list(dict.fromkeys(extracted_facts))
        summary_core = " | ".join(unique_facts) if unique_facts else "Initial customer greeting and general inquiries discussed."

        if self.summary:
            self.summary = f"{self.summary} Prior context: {summary_core}"
        else:
            self.summary = f"Summary of earlier conversation: {summary_core}"

        return self.summary
