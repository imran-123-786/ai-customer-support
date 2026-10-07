import re
from typing import Literal


class EmotionDetector:
    def __init__(self):
        self.positive_words = {
            "good",
            "great",
            "awesome",
            "nice",
            "love",
            "happy",
            "thanks",
            "thank you",
            "excellent",
        }
        self.negative_words = {
            "bad",
            "angry",
            "upset",
            "hate",
            "issue",
            "problem",
            "worst",
            "refund",
            "complaint",
        }

    def detect(self, text: str) -> Literal["positive", "negative", "neutral"]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())

        positive_hits = sum(1 for w in self.positive_words if w in cleaned)
        negative_hits = sum(1 for w in self.negative_words if w in cleaned)

        if positive_hits > negative_hits:
            return "positive"
        if negative_hits > positive_hits:
            return "negative"
        return "neutral"
