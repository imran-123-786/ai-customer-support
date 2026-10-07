"""
AI Failure Taxonomy and Root Cause Diagnostic Engine.
Classifies execution breakdowns into actionable failure categories.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from support_agent.models.schemas import FailureCategory


class FailureTaxonomyDebugger:
    @staticmethod
    def diagnose_failure(
        user_message: str,
        retrieval_count: int,
        tool_failures: list[dict],
        steps_taken: int,
        max_steps: int,
        exception_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze execution signals and classify root cause failure.
        """
        if tool_failures:
            failed_tool = tool_failures[0]
            return {
                "category": FailureCategory.TOOL_FAILURE.value,
                "reason": f"Tool '{failed_tool.get('tool_name')}' failed during execution: {failed_tool.get('error')}",
                "remediation": "Check database table foreign key constraints, API endpoint connectivity, or argument types.",
            }

        if steps_taken >= max_steps:
            return {
                "category": FailureCategory.APPLICATION_FAILURE.value,
                "reason": f"Agent loop exceeded maximum step limit ({max_steps} iterations) without convergence.",
                "remediation": "Tune action selection prompt or increase MAX_AGENT_STEPS.",
            }

        if "policy" in user_message.lower() and retrieval_count == 0:
            return {
                "category": FailureCategory.RETRIEVAL_FAILURE.value,
                "reason": "Knowledge base returned 0 relevant document chunks for policy question.",
                "remediation": "Verify document parser, re-index uploaded knowledge base, or lower confidence threshold.",
            }

        if exception_str and "json" in exception_str.lower():
            return {
                "category": FailureCategory.PARSING_FAILURE.value,
                "reason": f"Structured JSON output from model could not be deserialized: {exception_str}",
                "remediation": "Use stricter JSON schema prompt or Pydantic retry parser.",
            }

        return {
            "category": FailureCategory.MODEL_FAILURE.value,
            "reason": "Model produced ungrounded or non-convergent response.",
            "remediation": "Inspect system prompt grounding instructions.",
        }


taxonomy_debugger = FailureTaxonomyDebugger()
