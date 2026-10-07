import os
from dataclasses import dataclass

import requests

from emotion import EmotionDetector
from memory import ChatMemory
from utils import find_faq_answer, load_faq
from voice import VoiceSupport


@dataclass
class ChatResult:
    reply: str
    emotion: str
    source: str
    voice_text: str
    language: str
    citations: list[dict]


class ChatBot:
    def __init__(self):
        self.memory = ChatMemory()
        self.faq = load_faq()
        self.emotion = EmotionDetector()
        self.voice = VoiceSupport()

        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "30"))

    def _guess_language(self, text: str) -> str:
        if any("\u0980" <= ch <= "\u09ff" for ch in text):
            return "bn"
        if any("\u0900" <= ch <= "\u097f" for ch in text):
            return "hi"
        return "en"

    def _build_prompt(self, user_message: str, emotion: str, language: str, context: str) -> str:
        return (
            "You are a professional customer support assistant. "
            "Keep answers short, clear, and practical. "
            f"User emotion is {emotion}. "
            "If user sounds upset, reply with empathy first. "
            f"Reply in language code: {language}. "
            f"Use this context if relevant: {context}. "
            f"User message: {user_message}"
        )

    def _ask_llama(self, user_message: str, emotion: str, language: str, context: str) -> str | None:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": self._build_prompt(user_message, emotion, language, context),
                "stream": False,
            }
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            text = data.get("response", "").strip()
            if not text:
                return None
            return text
        except Exception:
            return None

    def _faq_or_default(self, user_message: str, language: str) -> str:
        faq_answer = find_faq_answer(user_message, self.faq)
        if faq_answer:
            return faq_answer

        if language == "hi":
            return (
                "मुझे अभी सटीक उत्तर नहीं मिला। "
                "कृपया अपना अकाउंट ईमेल या ऑर्डर आईडी शेयर करें।"
            )
        if language == "bn":
            return (
                "আমি এখন সঠিক উত্তর পাইনি। "
                "দয়া করে আপনার অ্যাকাউন্ট ইমেইল বা অর্ডার আইডি দিন।"
            )
        return (
            "I could not find an exact answer right now. "
            "Please share your account email or order id so I can help better."
        )

    def reply(
        self,
        user_message: str,
        preferred_language: str | None = None,
        context_snippets: list[str] | None = None,
        citations: list[dict] | None = None,
    ) -> ChatResult:
        # Delegate to SupportAgent Orchestrator
        try:
            from support_agent.agent.orchestrator import orchestrator
            state = orchestrator.run(
                user_message=text,
                history=[{"role": m.get("role", "user"), "text": m.get("text", "")} for m in self.memory.get_all()],
            )
            answer = state.final_response or self._faq_or_default(text, language)
            user_emotion = state.emotion or user_emotion
            source = "agent+tools" if state.tool_calls else ("rag" if state.retrieved_documents else "direct")
            citations_res = state.citations or (citations or [])
        except Exception:
            ai_reply = self._ask_llama(text, user_emotion, language, context_text)
            if ai_reply:
                answer = ai_reply
                source = "rag+llama" if context_text else "llama"
            else:
                answer = self._faq_or_default(text, language)
                source = "faq"
            citations_res = citations or []

        self.memory.add("user", text)
        self.memory.add("bot", answer)

        voice_text = self.voice.to_voice_text(answer)

        return ChatResult(
            reply=answer,
            emotion=user_emotion,
            source=source,
            voice_text=voice_text,
            language=language,
            citations=citations_res,
        )
