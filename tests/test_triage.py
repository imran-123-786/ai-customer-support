"""
Unit tests for TriageEngine.
"""
from support_agent.agent.triage import triage_engine


def test_triage_billing_intent():
    res = triage_engine.triage("I want a refund for my last order")
    assert res.intent == "Billing & Refund"


def test_triage_order_intent():
    res = triage_engine.triage("Where is my delivery tracking number?")
    assert res.intent == "Order Tracking"


def test_triage_critical_priority():
    res = triage_engine.triage("My account was hacked and there is security fraud!")
    assert res.priority == "Critical"
    assert res.intent == "Account Access"


def test_triage_emotion_detection():
    res = triage_engine.triage("This is terrible, I am furious with this delay!")
    assert res.emotion == "angry"
    assert res.priority == "High"
