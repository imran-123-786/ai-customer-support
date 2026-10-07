"""
Documents and Knowledge Base API route.
"""
from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel
try:
    from fastapi import APIRouter, File, UploadFile
except ImportError:
    APIRouter = None

from support_agent.rag.store import doc_store


class SearchDocsRequest(BaseModel):
    query: str
    top_k: int = 3


if APIRouter:
    router = APIRouter(prefix="/documents", tags=["Documents"])

    @router.get("")
    def get_documents_count():
        return {"total_chunks": len(doc_store.chunks)}

    @router.post("/search")
    def search_documents(req: SearchDocsRequest):
        results = doc_store.search(req.query, top_k=req.top_k)
        return [
            {
                "source": chunk.source,
                "section": chunk.section,
                "snippet": chunk.content[:200],
                "score": round(score, 3),
            }
            for chunk, score in results
        ]
else:
    router = None
