"""
Simple RAG service using TF-IDF.
Pure Python - no heavy ML libraries.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
import math
import re

from pypdf import PdfReader


@dataclass
class Citation:
    source: str
    chunk: str
    score: float


class RagService:
    def __init__(self):
        base = Path(__file__).resolve().parent
        self.docs_dir = base / "uploaded_docs"
        self.docs_dir.mkdir(exist_ok=True)
        
        self.index_file = base / "rag_index.json"
        self._load_index()

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])
                self.idf = data.get('idf', {})
        else:
            self.documents = []
            self.idf = {}

    def _save_index(self):
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({'documents': self.documents, 'idf': self.idf}, f)

    def _tokenize(self, text: str) -> list:
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'be', 'have', 'has', 'do', 'does',
                     'will', 'would', 'could', 'to', 'of', 'in', 'for', 'on', 'with', 'at'}
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def _compute_tf(self, tokens: list) -> dict:
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        if tokens:
            for token in tf:
                tf[token] /= len(tokens)
        return tf

    def _compute_idf(self):
        n = len(self.documents)
        if n == 0:
            return
        df = {}
        for doc in self.documents:
            for token in set(doc['tokens']):
                df[token] = df.get(token, 0) + 1
        for token, count in df.items():
            self.idf[token] = math.log((n + 1) / (count + 1)) + 1

    def _chunk_text(self, text: str, size: int = 500, overlap: int = 50):
        text = " ".join(text.split())
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + size])
            start += size - overlap
        return [c for c in chunks if c.strip()]

    def _read_file(self, path: Path) -> str:
        try:
            if path.suffix.lower() == ".pdf":
                reader = PdfReader(str(path))
                pages = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                result = "\n".join(pages)
                if not result.strip():
                    return "PDF has no extractable text"
                return result
            elif path.suffix.lower() == ".csv":
                import csv
                rows = []
                with open(str(path), 'r', encoding='utf-8', errors='ignore') as f:
                    for row in csv.reader(f):
                        rows.append(" | ".join(row))
                return "\n".join(rows)
            elif path.suffix.lower() == ".json":
                with open(str(path), 'r', encoding='utf-8', errors='ignore') as f:
                    return json.dumps(json.load(f), indent=2)
            else:
                return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"Error: {str(e)}"

    def add_document(self, user_id: int, filename: str, file_bytes: bytes) -> int:
        safe_name = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
        file_path = self.docs_dir / safe_name
        file_path.write_bytes(file_bytes)

        text = self._read_file(file_path)
        chunks = self._chunk_text(text)
        if not chunks:
            return 0

        for chunk in chunks:
            tokens = self._tokenize(chunk)
            tf = self._compute_tf(tokens)
            self.documents.append({
                'id': str(uuid.uuid4().hex),
                'user_id': user_id,
                'source': filename,
                'text': chunk,
                'tokens': tokens,
                'tf': tf
            })
        
        self._compute_idf()
        self._save_index()
        return len(chunks)

    def search(self, user_id: int, query: str, top_k: int = 3) -> list[Citation]:
        user_docs = [d for d in self.documents if d['user_id'] == user_id]
        if not user_docs:
            return []
        
        query_tokens = self._tokenize(query)
        query_tf = self._compute_tf(query_tokens)
        
        scores = []
        for doc in user_docs:
            score = 0.0
            for token, tf in query_tf.items():
                if token in doc['tf']:
                    idf = self.idf.get(token, 1.0)
                    score += tf * idf * doc['tf'].get(token, 0)
            if score > 0:
                scores.append((doc, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return [Citation(source=doc['source'], chunk=doc['text'], score=score) 
                for doc, score in scores[:top_k]]


rag_service = RagService()
