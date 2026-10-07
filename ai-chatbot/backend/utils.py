import json
import os


def load_faq():
    base = os.path.dirname(os.path.abspath(__file__))
    faq_path = os.path.join(base, "..", "data", "faq.json")

    if not os.path.exists(faq_path):
        return []

    with open(faq_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def find_faq_answer(user_text: str, faq_list):
    user_low = user_text.lower()
    for item in faq_list:
        question = item.get("question", "").lower()
        if question and question in user_low:
            return item.get("answer", "")
    return None
