import re


class VoiceSupport:
    def __init__(self):
        self.voice_commands = ["speak", "read this", "voice mode", "audio"]

    def wants_voice(self, user_text: str) -> bool:
        low = user_text.lower()
        return any(cmd in low for cmd in self.voice_commands)

    def to_voice_text(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    def to_ssml(self, text: str) -> str:
        clean = self.to_voice_text(text)
        return f"<speak><prosody rate='95%'>{clean}</prosody></speak>"
