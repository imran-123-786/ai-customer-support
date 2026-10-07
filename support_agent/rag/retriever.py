"""
Retriever module for verified citations and grounded context retrieval.
"""
from __future__ import annotations

from typing import List, Optional
from support_agent.models.schemas import RetrievedDocument
from support_agent.rag.store import doc_store


class KnowledgeRetriever:
    def __init__(self, confidence_threshold: float = 0.25):
        self.store = doc_store
        self.confidence_threshold = confidence_threshold

    def search(self, query: str, top_k: int = 3) -> List[RetrievedDocument]:
        scored_chunks = self.store.search(query, top_k=top_k)
        retrieved: List[RetrievedDocument] = []

        for chunk, score in scored_chunks:
            retrieved.append(
                RetrievedDocument(
                    source=chunk.source,
                    section=chunk.section,
                    chunk=chunk.content,
                    score=round(score, 3),
                )
            )
        return retrieved

    def has_sufficient_knowledge(self, documents: List[RetrievedDocument]) -> bool:
        if not documents:
            return False
        return any(doc.score >= self.confidence_threshold for doc in documents)

    def format_citations(self, documents: List[RetrievedDocument]) -> List[dict]:
        citations = []
        for d in documents:
            citations.append({
                "source": d.source,
                "section": d.section or "Main Document",
                "score": d.score,
                "snippet": d.chunk[:180] + "..." if len(d.chunk) > 180 else d.chunk,
            })
        return citations


retriever = KnowledgeRetriever()
