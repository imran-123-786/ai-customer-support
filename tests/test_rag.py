"""
Unit tests for RAG parser, chunker, store, and retriever.
"""
from support_agent.rag.retriever import retriever
from support_agent.rag.store import doc_store


def test_knowledge_base_loaded():
    assert len(doc_store.chunks) > 0, "Default knowledge chunks not loaded into store"


def test_refund_policy_search():
    hits = retriever.search("What is the return window?", top_k=3)
    assert len(hits) > 0
    assert any("refund" in h.source.lower() for h in hits)
    assert hits[0].score > 0.15


def test_shipping_policy_search():
    hits = retriever.search("How many days for standard shipping delivery?", top_k=3)
    assert len(hits) > 0
    assert any("shipping" in h.source.lower() for h in hits)
