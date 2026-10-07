"""
SupportAgent AI - Automated Verification & Demonstration Script.
Executes database seeding, unit tests, 25-scenario evaluation suite,
and prints key multi-step agent demonstrations.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from support_agent.database.seed_data import seed_database
from support_agent.evaluation.runner import evaluator
from support_agent.agent.orchestrator import orchestrator


def main():
    print("=" * 65)
    print(" SupportAgent AI — Production Verification Suite ")
    print("=" * 65)

    print("\n[1/3] Initializing and Seeding Synthetic Enterprise Database...")
    seed_database(force=True)
    print("  -> Database seeded with customers, orders, payments, tickets, and memories.")

    print("\n[2/3] Executing 25-Scenario Benchmark Evaluation Suite...")
    eval_metrics = evaluator.run_all()
    print(f"  -> Total Scenarios: {eval_metrics['total_cases']}")
    print(f"  -> Passed: {eval_metrics['passed_cases']}")
    print(f"  -> Overall Accuracy: {eval_metrics['overall_accuracy_percent']}%")
    print(f"  -> Intent Accuracy: {eval_metrics['intent_accuracy_percent']}%")
    print(f"  -> Tool Selection Accuracy: {eval_metrics['tool_accuracy_percent']}%")
    print(f"  -> Escalation Accuracy: {eval_metrics['escalation_accuracy_percent']}%")

    print("\n[3/3] Demonstrating Multi-Step Autonomous Agent Workflows...")

    # Scenario 1: Order Tracking
    print("\n--- DEMO 1: Order Tracking Lookup ---")
    s1 = orchestrator.run("Where is my order ORD-1001?")
    print(f"User: Where is my order ORD-1001?")
    print(f"Tools Executed: {[t.tool_name for t in s1.tool_calls]}")
    print(f"Agent Response:\n{s1.final_response}")

    # Scenario 2: Multi-Step Duplicate Charge & Refund
    print("\n--- DEMO 2: Multi-Step Duplicate Charge Resolution ---")
    s2 = orchestrator.run("I was charged twice for ORD-1024 and I want a refund.")
    print(f"User: I was charged twice for ORD-1024 and I want a refund.")
    print(f"Tools Executed: {[t.tool_name for t in s2.tool_calls]}")
    print(f"Agent Response:\n{s2.final_response}")

    # Scenario 3: Human Escalation & Handoff Summary
    print("\n--- DEMO 3: Human Escalation & Briefing ---")
    s3 = orchestrator.run("I've been trying for three days and nobody is helping me. Connect me to a human.")
    print(f"User: I've been trying for three days and nobody is helping me. Connect me to a human.")
    print(f"Escalation Triggered: {s3.escalation_required} (Priority: {s3.priority})")
    print(f"Tools Executed: {[t.tool_name for t in s3.tool_calls]}")
    print(f"Agent Response:\n{s3.final_response}")

    # Scenario 4: Grounded Knowledge Retrieval (RAG)
    print("\n--- DEMO 4: Grounded RAG with Policy Citations ---")
    s4 = orchestrator.run("What is your refund policy?")
    print(f"User: What is your refund policy?")
    print(f"Sources Retrieved: {[c['source'] for c in s4.citations]}")
    print(f"Agent Response:\n{s4.final_response}")

    print("\n" + "=" * 65)
    print(" All systems operational! Ready for review or Streamlit launch: ")
    print("   streamlit run app.py ")
    print("=" * 65)


if __name__ == "__main__":
    main()
