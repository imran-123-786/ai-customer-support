"""
Unit tests for short-term and long-term customer memory.
"""
from support_agent.memory.long_term import customer_memory
from support_agent.memory.short_term import ConversationMemory
from support_agent.memory.extractor import memory_extractor
from support_agent.models.schemas import MemoryItem


def test_short_term_memory_window_and_compression():
    mem = ConversationMemory(recent_limit=4)
    mem.add_message("user", "Hello, I have an issue with ORD-1024.")
    mem.add_message("assistant", "I see ORD-1024. How can I help?")
    mem.add_message("user", "I was charged twice on my card.")
    mem.add_message("assistant", "Let me check the duplicate charge.")
    mem.add_message("user", "I also want a refund.")
    mem.add_message("assistant", "Checking refund eligibility.")
    mem.add_message("user", "Please reply in Hindi next time.")
    mem.add_message("assistant", "Noted.")
    mem.add_message("user", "Is my ticket ready?")
    mem.add_message("assistant", "Ticket TICK-8002 created.")

    summary = mem.compress()
    assert "ORD-1024" in summary or "TICK-8002" in summary or "refund" in summary.lower()
    recent = mem.get_recent_messages()
    assert len(recent) <= 4


def test_customer_memory_persistence():
    cust_id = "CUST-TEST-99"
    item = MemoryItem(
        memory_type="preference",
        key="test_pref",
        value="Prefers fast delivery notifications",
        confidence=0.9,
    )
    saved = customer_memory.save_memory(cust_id, item)
    assert saved is True

    loaded = customer_memory.get_memories(cust_id)
    assert any(m.key == "test_pref" and "fast delivery" in m.value for m in loaded)


def test_memory_security_rejection():
    # Attempting to store password or credit card should be blocked
    cust_id = "CUST-TEST-99"
    bad_item = MemoryItem(
        memory_type="preference",
        key="stolen_card",
        value="Customer credit card 4111-2222-3333-4444",
        confidence=1.0,
    )
    saved = customer_memory.save_memory(cust_id, bad_item)
    assert saved is False


def test_memory_extraction():
    cand = memory_extractor.extract_from_message("CUST-104", "I always prefer Hindi responses")
    assert cand.should_remember is True
    assert any(m.key == "preferred_language" and "Hindi" in m.value for m in cand.memories)
