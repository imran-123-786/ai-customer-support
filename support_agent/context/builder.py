"""
ContextBuilder for SupportAgent AI.
Assembles, estimates, prioritizes, and manages token budgets for LLM context.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from support_agent.config import CONTEXT_TOKEN_LIMIT
from support_agent.models.schemas import AgentState, RetrievedDocument, ToolResultRecord


class ContextBuilder:
    def __init__(self, max_tokens: int = CONTEXT_TOKEN_LIMIT):
        self.max_tokens = max_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimation (~4 characters per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def prioritize_context(
        self,
        system_instruction: str,
        user_message: str,
        tool_results: List[ToolResultRecord],
        retrieved_docs: List[RetrievedDocument],
        long_term_memory: str,
        conversation_summary: str,
        recent_messages: List[Dict[str, Any]],
    ) -> str:
        """
        Assembles context in strict priority order:
        Priority 1: System Instructions & Grounding Rules (mandatory)
        Priority 2: Current User Request (mandatory)
        Priority 3: Tool Execution Results (highest dynamic context)
        Priority 4: Retrieved Knowledge Base Citations
        Priority 5: Persistent Long-Term Customer Memory
        Priority 6: Rolling Conversation Summary
        Priority 7: Recent Conversation Turns
        """
        sections: List[str] = []

        # 1. System Prompt
        sections.append(f"### SYSTEM INSTRUCTIONS\n{system_instruction.strip()}")

        # 2. Tool Results (if any tools executed in this step)
        if tool_results:
            tool_texts = []
            for tr in tool_results:
                res_str = json.dumps(tr.result, indent=2) if isinstance(tr.result, (dict, list)) else str(tr.result)
                status_str = "SUCCESS" if tr.success else f"FAILED: {tr.error_message}"
                tool_texts.append(f"Tool `{tr.tool_name}` [{status_str}]:\n{res_str}")
            sections.append("### TOOL EXECUTION RESULTS\n" + "\n\n".join(tool_texts))

        # 3. Retrieved Knowledge (RAG)
        if retrieved_docs:
            doc_texts = []
            for doc in retrieved_docs:
                doc_texts.append(f"Source: {doc.source} ({doc.section or 'General'})\nRelevance Score: {doc.score}\nContent: {doc.chunk}")
            sections.append("### VERIFIED KNOWLEDGE BASE DOCUMENTS\n" + "\n\n".join(doc_texts))

        # 4. Long-Term Customer Memory
        if long_term_memory.strip():
            sections.append(f"### CUSTOMER PROFILE & PERSISTENT MEMORY\n{long_term_memory.strip()}")

        # 5. Conversation Summary
        if conversation_summary.strip():
            sections.append(f"### EARLIER CONVERSATION SUMMARY\n{conversation_summary.strip()}")

        # 6. Recent Conversation
        if recent_messages:
            msg_texts = []
            for m in recent_messages[-6:]:
                role = m.get("role", "user").upper()
                text = m.get("text", "")
                msg_texts.append(f"{role}: {text}")
            sections.append("### RECENT DIALOGUE\n" + "\n".join(msg_texts))

        # 7. Current User Message
        sections.append(f"### CURRENT CUSTOMER MESSAGE\n{user_message.strip()}")

        assembled = "\n\n========================================\n\n".join(sections)
        return self.truncate_context(assembled, self.max_tokens)

    def truncate_context(self, context_text: str, token_budget: int) -> str:
        current_tokens = self.estimate_tokens(context_text)
        if current_tokens <= token_budget:
            return context_text

        # Truncate safe character slice
        max_chars = token_budget * 4
        return context_text[:max_chars] + "\n\n[Warning: Context budget reached, older context truncated.]"

    def build_from_state(self, state: AgentState, system_prompt: str) -> str:
        memory_str = "\n".join([f"- {m.get('memory_type', 'preference')}: {m.get('memory_value', '')}" for m in state.long_term_memory])
        return self.prioritize_context(
            system_instruction=system_prompt,
            user_message=state.current_message,
            tool_results=state.tool_results,
            retrieved_docs=state.retrieved_documents,
            long_term_memory=memory_str,
            conversation_summary=state.conversation_summary,
            recent_messages=state.short_term_memory,
        )


context_builder = ContextBuilder()
