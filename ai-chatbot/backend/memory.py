class ChatMemory:
    def __init__(self):
        self.items = []

    def add(self, role: str, text: str):
        self.items.append({"role": role, "text": text})

    def get_all(self):
        return self.items
