"""
Memory extraction pipeline.
Extracts durable, verified facts and preferences from customer interaction turns
and persists them to long-term memory.
"""
from __future__ import annotations

import re
from typing import List, Optional
from support_agent.memory.long_term import customer_memory
from support_agent.models.schemas import MemoryExtractionCandidate, MemoryItem


class MemoryExtractor:
    def __init__(self):
        pass

    def extract_from_message(self, customer_id: str, message: str) -> MemoryExtractionCandidate:
        """
        Analyze customer text for explicit declarations of durable preferences.
        """
        text = message.strip()
        lower = text.lower()
        memories: List[MemoryItem] = []

        # 1. Language Preferences
        if any(p in lower for p in ["always prefer hindi", "speak in hindi", "reply in hindi", "hindi responses", "hindi please"]):
            memories.append(
                MemoryItem(
                    memory_type="language_preference",
                    key="preferred_language",
                    value="Hindi responses",
                    confidence=0.95,
                )
            )
        elif any(p in lower for p in ["always prefer bengali", "reply in bengali", "bangla please", "bengali responses"]):
            memories.append(
                MemoryItem(
                    memory_type="language_preference",
                    key="preferred_language",
                    value="Bengali responses",
                    confidence=0.95,
                )
            )
        elif any(p in lower for p in ["english only", "prefer english", "reply in english"]):
            memories.append(
                MemoryItem(
                    memory_type="language_preference",
                    key="preferred_language",
                    value="English responses",
                    confidence=0.95,
                )
            )

        # 2. Communication Style Preferences
        if any(p in lower for p in ["keep it short", "bullet points only", "be concise", "concise answers"]):
            memories.append(
                MemoryItem(
                    memory_type="style_preference",
                    key="communication_style",
                    value="Prefers concise, bullet-pointed summaries",
                    confidence=0.90,
                )
            )

        # 3. Known Hardware/Environment
        if "macbook" in lower or "macos" in lower:
            memories.append(
                MemoryItem(
                    memory_type="known_issue",
                    key="operating_system",
                    value="macOS environment",
                    confidence=0.85,
                )
            )
        elif "windows 11" in lower:
            memories.append(
                MemoryItem(
                    memory_type="known_issue",
                    key="operating_system",
                    value="Windows 11 environment",
                    confidence=0.85,
                )
            )

        candidate = MemoryExtractionCandidate(
            should_remember=len(memories) > 0,
            memories=memories,
        )

        # Persist extracted memories
        for mem in memories:
            customer_memory.save_memory(customer_id, mem)

        return candidate


memory_extractor = MemoryExtractor()
