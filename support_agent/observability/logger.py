"""
Observability and Telemetry aggregator.
Provides analytics summaries for agent runs, tool performance, and failure categorization.
"""
from __future__ import annotations

from typing import Any, Dict, List
from support_agent.database.repository import repo


class ObservabilityManager:
    def __init__(self):
        self.repo = repo

    def get_system_telemetry(self) -> Dict[str, Any]:
        runs = self.repo.get_agent_runs(limit=100)
        tool_calls = self.repo.get_tool_calls(limit=100)
        feedback = self.repo.get_feedback_metrics()

        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r.get("success", 1) == 1)
        escalated_runs = sum(1 for r in runs if r.get("escalated", 0) == 1)
        resolution_rate = round((successful_runs / total_runs * 100), 1) if total_runs else 100.0

        total_tool_calls = len(tool_calls)
        successful_tools = sum(1 for t in tool_calls if t.get("success", 1) == 1)
        tool_success_rate = round((successful_tools / total_tool_calls * 100), 1) if total_tool_calls else 100.0
        avg_tool_latency = (
            round(sum(t.get("latency_ms", 0.0) for t in tool_calls) / total_tool_calls, 1)
            if total_tool_calls
            else 0.0
        )

        # Failure category breakdown
        failures: Dict[str, int] = {}
        for r in runs:
            cat = r.get("failure_category")
            if cat:
                failures[cat] = failures.get(cat, 0) + 1

        return {
            "total_runs": total_runs,
            "resolution_rate": resolution_rate,
            "escalation_count": escalated_runs,
            "total_tool_calls": total_tool_calls,
            "tool_success_rate": tool_success_rate,
            "avg_tool_latency_ms": avg_tool_latency,
            "avg_csat": feedback.get("avg_csat", 5.0),
            "failure_breakdown": failures,
        }


observability_manager = ObservabilityManager()
