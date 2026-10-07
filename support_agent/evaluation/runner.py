"""
SupportAgent Benchmark Evaluation Runner.
Evaluates agent performance across 25 realistic support scenarios.
Calculates Intent Accuracy, Tool Accuracy, Retrieval Relevance, Escalation Accuracy, and Overall Score.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from support_agent.agent.orchestrator import orchestrator
from support_agent.database.repository import repo


class BenchmarkEvaluator:
    def __init__(self):
        eval_file = Path(__file__).resolve().parent / "customer_support_eval.json"
        with open(eval_file, "r", encoding="utf-8") as f:
            self.test_cases = json.load(f)

    def run_all(self) -> Dict[str, Any]:
        eval_id = f"eval-{uuid.uuid4().hex[:8]}"
        results: List[Dict[str, Any]] = []

        intent_correct = 0
        tool_correct = 0
        escalation_correct = 0
        retrieval_correct = 0
        total = len(self.test_cases)

        for tc in self.test_cases:
            tc_id = tc["id"]
            user_input = tc["input"]
            expected_intent = tc["expected_intent"]
            expected_tool = tc["expected_tool"]
            expected_escalation = tc["expected_escalation"]
            expected_sources = tc.get("expected_sources", [])

            # Execute orchestrator
            state = orchestrator.run(user_message=user_input, customer_id="CUST-104")

            # 1. Intent check
            intent_pass = state.intent == expected_intent
            if intent_pass:
                intent_correct += 1

            # 2. Tool check
            tools_called = [tc.tool_name for tc in state.tool_calls]
            if expected_tool is None:
                tool_pass = len(tools_called) == 0 or (state.retrieved_documents and len(tools_called) == 0)
            else:
                tool_pass = expected_tool in tools_called
            if tool_pass:
                tool_correct += 1

            # 3. Escalation check
            esc_pass = state.escalation_required == expected_escalation
            if esc_pass:
                escalation_correct += 1

            # 4. Retrieval check
            if expected_sources:
                sources_retrieved = [doc.source for doc in state.retrieved_documents]
                rag_pass = any(s in sources_retrieved for s in expected_sources)
            else:
                rag_pass = True
            if rag_pass:
                retrieval_correct += 1

            overall_tc_pass = intent_pass and tool_pass and esc_pass and rag_pass
            results.append({
                "id": tc_id,
                "name": tc["name"],
                "passed": overall_tc_pass,
                "intent_match": intent_pass,
                "tool_match": tool_pass,
                "escalation_match": esc_pass,
                "retrieval_match": rag_pass,
                "detected_intent": state.intent,
                "tools_executed": tools_called,
                "escalated": state.escalation_required,
            })

        passed_count = sum(1 for r in results if r["passed"])
        overall_accuracy = round((passed_count / total) * 100, 2)
        metrics = {
            "total_cases": total,
            "passed_cases": passed_count,
            "overall_accuracy_percent": overall_accuracy,
            "intent_accuracy_percent": round((intent_correct / total) * 100, 2),
            "tool_accuracy_percent": round((tool_correct / total) * 100, 2),
            "escalation_accuracy_percent": round((escalation_correct / total) * 100, 2),
            "retrieval_accuracy_percent": round((retrieval_correct / total) * 100, 2),
            "case_results": results,
        }

        # Persist to database
        repo.save_evaluation_run(
            eval_id=eval_id,
            eval_name="SupportAgent Benchmark Suite (25 Scenarios)",
            total_cases=total,
            passed_cases=passed_count,
            accuracy=overall_accuracy,
            metrics=metrics,
        )

        return metrics


evaluator = BenchmarkEvaluator()

if __name__ == "__main__":
    print("Executing SupportAgent Evaluation Suite...")
    summary = evaluator.run_all()
    print(f"Total Cases: {summary['total_cases']}")
    print(f"Passed Cases: {summary['passed_cases']}")
    print(f"Overall Accuracy: {summary['overall_accuracy_percent']}%")
    print(f"Intent Accuracy: {summary['intent_accuracy_percent']}%")
    print(f"Tool Selection Accuracy: {summary['tool_accuracy_percent']}%")
    print(f"Escalation Accuracy: {summary['escalation_accuracy_percent']}%")
