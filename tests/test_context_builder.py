"""
Unit tests for ContextBuilder prioritizing and token budgeting.
"""
from support_agent.context.builder import ContextBuilder
from support_agent.models.schemas import ToolResultRecord, RetrievedDocument


def test_context_builder_token_estimation():
    builder = ContextBuilder(max_tokens=500)
    text = "A quick brown fox jumps over the lazy dog."
    tokens = builder.estimate_tokens(text)
    assert tokens > 0
    assert tokens == len(text) // 4


def test_context_builder_prioritization():
    builder = ContextBuilder(max_tokens=1000)
    ctx = builder.prioritize_context(
        system_instruction="Strict Support Rules",
        user_message="I was charged twice",
        tool_results=[ToolResultRecord(call_id="c1", tool_name="get_payment_status", result={"duplicate": True}, success=True)],
        retrieved_docs=[RetrievedDocument(source="Policy.md", section="Section 3", chunk="Duplicate refund rules", score=0.9)],
        long_term_memory="- language: Hindi",
        conversation_summary="Prior discussion on ORD-1024",
        recent_messages=[{"role": "user", "text": "Need help"}],
    )
    assert "Strict Support Rules" in ctx
    assert "get_payment_status" in ctx
    assert "Policy.md" in ctx
    assert "Hindi" in ctx
    assert "I was charged twice" in ctx


def test_context_builder_truncation():
    builder = ContextBuilder(max_tokens=20)
    long_text = "Word " * 200
    truncated = builder.truncate_context(long_text, token_budget=20)
    assert len(truncated) < len(long_text)
    assert "truncated" in truncated.lower()
