"""
Triage engine for intent classification, emotion detection, and SLA priority routing.
Transparent, rules-grounded logic with realistic support heuristics.
"""
from __future__ import annotations

import re
from support_agent.models.schemas import TriageResult


class TriageEngine:
    def __init__(self):
        self.intent_keywords = {
            "Billing & Refund": ["refund", "refundable", "return", "charge", "charged", "billing", "invoice", "payment", "deducted", "money back", "duplicate"],
            "Order Tracking": ["track", "tracking", "status", "where is", "shipped", "shipping", "shipment", "delivery", "carrier", "transit", "package", "parcel", "arrive"],
            "Account Access": ["login", "password", "2fa", "two-factor", "account", "locked", "compromise", "hacked", "reset", "email"],
            "Technical Issue": ["error", "bug", "crash", "not working", "broken", "failed", "glitch", "screen", "disconnect"],
            "Cancellation": ["cancel", "stop order", "revoke", "terminate"],
            "Complaint": ["worst", "terrible", "unacceptable", "scam", "cheat", "sue", "lawyer", "angry", "delay"],
        }

        self.emotion_lexicon = {
            "angry": ["furious", "unacceptable", "scam", "ridiculous", "cheat", "sue", "lawsuit", "disgusting", "terrible"],
            "frustrated": ["again", "trying for", "nobody is helping", "still waiting", "three days", "hours", "fed up", "useless"],
            "worried": ["concerned", "scared", "fear", "anxious", "lost", "nervous", "missing"],
            "confused": ["why", "how", "don't understand", "clarify", "what does this mean", "not clear"],
            "urgent": ["asap", "emergency", "immediately", "urgent", "right now", "hurry"],
            "positive": ["thanks", "thank you", "great", "awesome", "perfect", "good", "helpful", "appreciate"],
        }

    def classify_intent(self, text: str) -> str:
        lower = text.lower()
        for intent, kws in self.intent_keywords.items():
            if any(k in lower for k in kws):
                return intent
        return "General Inquiry"

    def detect_emotion(self, text: str) -> str:
        lower = text.lower()
        for emotion, words in self.emotion_lexicon.items():
            if any(w in lower for w in words):
                return emotion
        return "neutral"

    def calculate_priority(self, text: str, emotion: str, intent: str) -> str:
        lower = text.lower()
        # Critical
        if any(w in lower for w in ["fraud", "hacked", "compromise", "legal", "lawyer", "lawsuit", "police", "stolen"]):
            return "Critical"
        if emotion in ("angry", "urgent") or "charged twice" in lower or "duplicate" in lower:
            return "High"
        if emotion in ("frustrated", "worried") or intent in ("Billing & Refund", "Technical Issue"):
            return "Medium"
        return "Low"

    def suggest_actions(self, intent: str) -> list[str]:
        actions = {
            "Billing & Refund": ["Verify order ID", "Check payment gateway records", "Initiate refund if eligible"],
            "Order Tracking": ["Inspect carrier tracking number", "Confirm shipping address", "Check delivery milestone"],
            "Account Access": ["Verify customer email", "Send secure password reset link", "Check account freeze status"],
            "Technical Issue": ["Collect browser/device details", "Check service health", "Create technical diagnostic ticket"],
            "Cancellation": ["Verify order shipment status", "Cancel if pending", "Queue standard return if in transit"],
            "Complaint": ["Acknowledge inconvenience", "Offer priority human escalation", "Log incident report"],
            "General Inquiry": ["Search support knowledge base", "Provide verified documentation links"],
        }
        return actions.get(intent, ["Search knowledge base", "Offer assistance"])

    def triage(self, text: str) -> TriageResult:
        intent = self.classify_intent(text)
        emotion = self.detect_emotion(text)
        priority = self.calculate_priority(text, emotion, intent)
        actions = self.suggest_actions(intent)
        return TriageResult(
            intent=intent,
            emotion=emotion,
            priority=priority,
            confidence=0.92,
            suggested_actions=actions,
        )


triage_engine = TriageEngine()
