"""
Semantic and sliding-window chunker with section preservation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    chunk_id: str
    source: str
    section: str
    content: str
    metadata: Dict[str, Any] = {}


class DocumentChunker:
    def __init__(self, chunk_size: int = 400, overlap: int = 60):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_section(self, source_name: str, section_name: str, text: str) -> List[DocumentChunk]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []

        chunks: List[DocumentChunk] = []
        if len(cleaned) <= self.chunk_size:
            chunk_id = f"{source_name}::{section_name}::0"
            return [DocumentChunk(chunk_id=chunk_id, source=source_name, section=section_name, content=cleaned)]

        start = 0
        idx = 0
        while start < len(cleaned):
            end = min(start + self.chunk_size, len(cleaned))
            # Try to break at sentence or space boundary
            if end < len(cleaned):
                last_space = cleaned.rfind(" ", start, end)
                if last_space > start + (self.chunk_size // 2):
                    end = last_space

            slice_text = cleaned[start:end].strip()
            if slice_text:
                chunk_id = f"{source_name}::{section_name}::{idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source=source_name,
                        section=section_name,
                        content=slice_text,
                        metadata={"start_char": start, "end_char": end},
                    )
                )
                idx += 1

            start += self.chunk_size - self.overlap
            if start >= len(cleaned) or end == len(cleaned):
                break

        return chunks
