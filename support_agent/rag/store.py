"""
Hybrid Vector / Lexical Document Store for SupportAgent AI.
Supports indexing documents, computing term frequencies and inverted index,
and hybrid similarity scoring.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from support_agent.config import PACKAGE_ROOT
from support_agent.rag.chunker import DocumentChunk, DocumentChunker
from support_agent.rag.parser import DocumentParser


class DocumentStore:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.doc_freq: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.chunker = DocumentChunker()
        self.parser = DocumentParser()

        # Load default knowledge base documents
        self._load_default_kb()

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = cleaned.split()
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "have", "has", "had",
            "do", "does", "did", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "and", "or", "so", "it", "this", "that", "i", "you", "we", "my"
        }
        return [t for t in tokens if len(t) > 1 and t not in stopwords]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
        if tokens:
            total = len(tokens)
            for t in tf:
                tf[t] = tf[t] / total
        return tf

    def _update_idf(self):
        n = len(self.chunks)
        if n == 0:
            return
        df: Dict[str, int] = {}
        for c in self.chunks:
            tokens = set(self._tokenize(c.content))
            for t in tokens:
                df[t] = df.get(t, 0) + 1
        self.doc_freq = df
        self.idf = {t: math.log((n + 1.0) / (cnt + 0.5)) + 1.0 for t, cnt in df.items()}

    def add_file(self, file_path: Path) -> int:
        sections = self.parser.parse_file(file_path)
        added_count = 0
        for sec in sections:
            sec_chunks = self.chunker.chunk_section(
                source_name=file_path.name,
                section_name=sec["section"],
                text=sec["text"],
            )
            self.chunks.extend(sec_chunks)
            added_count += len(sec_chunks)
        self._update_idf()
        return added_count

    def add_document_content(self, filename: str, content: bytes | str) -> int:
        tmp_dir = PACKAGE_ROOT / "data" / "uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        file_path = tmp_dir / filename
        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content, encoding="utf-8")
        return self.add_file(file_path)

    def _load_default_kb(self):
        kb_dir = PACKAGE_ROOT / "data" / "knowledge_base"
        if kb_dir.exists():
            for f in kb_dir.glob("*.*"):
                if f.suffix.lower() in (".md", ".txt", ".json", ".pdf", ".csv"):
                    self.add_file(f)

    def search(self, query: str, top_k: int = 3) -> List[tuple[DocumentChunk, float]]:
        if not self.chunks:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        q_tf = self._compute_tf(q_tokens)
        scored: List[tuple[DocumentChunk, float]] = []

        for chunk in self.chunks:
            c_tokens = self._tokenize(chunk.content)
            c_tf = self._compute_tf(c_tokens)

            # BM25-like TF-IDF score
            score = 0.0
            overlap = 0
            for t, tf_val in q_tf.items():
                if t in c_tf:
                    idf_val = self.idf.get(t, 1.0)
                    score += tf_val * idf_val * c_tf[t] * 10.0
                    overlap += 1

            # Exact phrase / title match bonus
            q_clean = query.lower()
            if q_clean in chunk.content.lower():
                score += 0.5
            if chunk.section and chunk.section.lower() in q_clean:
                score += 0.3

            # Normalization
            if score > 0:
                normalized_score = min(1.0, score / (1.0 + score))
                scored.append((chunk, normalized_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


doc_store = DocumentStore()
