"""
Persistent customer memory store.
Reads and writes durable customer preferences, language settings, and account context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from support_agent.database.repository import repo
from support_agent.models.schemas import MemoryItem


class CustomerMemoryStore:
    def __init__(self):
        self.repo = repo

    def get_memories(self, customer_id: str) -> List[MemoryItem]:
        records = self.repo.get_customer_memories(customer_id)
        return [
            MemoryItem(
                memory_type=r["memory_type"],
                key=r["memory_key"],
                value=r["memory_value"],
                confidence=r.get("confidence", 1.0),
            )
            for r in records
        ]

    def save_memory(self, customer_id: str, item: MemoryItem) -> bool:
        # Security & Privacy check: Never store sensitive credentials or credit card numbers
        lower_val = item.value.lower()
        if any(sens in lower_val for sens in ("password", "cvv", "credit card", "pin", "secret")):
            return False

        return self.repo.save_customer_memory(
            customer_id=customer_id,
            memory_type=item.memory_type,
            key=item.key,
            value=item.value,
            confidence=item.confidence,
        )

    def format_memory_for_context(self, customer_id: str) -> str:
        memories = self.get_memories(customer_id)
        if not memories:
            return ""

        lines = ["Customer Long-Term Preferences:"]
        for m in memories:
            lines.append(f"- {m.memory_type.replace('_', ' ').title()}: {m.value}")
        return "\n".join(lines)


customer_memory = CustomerMemoryStore()
