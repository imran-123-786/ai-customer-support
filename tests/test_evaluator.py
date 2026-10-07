"""
Unit tests for evaluation benchmark runner.
"""
from support_agent.evaluation.runner import evaluator


def test_evaluator_benchmark_execution():
    metrics = evaluator.run_all()
    assert metrics["total_cases"] == 25
    assert metrics["passed_cases"] >= 24
    assert metrics["overall_accuracy_percent"] >= 95.0
    assert metrics["intent_accuracy_percent"] == 100.0
    assert metrics["escalation_accuracy_percent"] == 100.0
