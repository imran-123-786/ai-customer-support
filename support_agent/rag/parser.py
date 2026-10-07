"""
Document parsers for PDF, TXT, MD, CSV, and JSON knowledge sources.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pypdf import PdfReader


class DocumentParser:
    @staticmethod
    def parse_file(file_path: Path) -> List[Dict[str, Any]]:
        """
        Parses file into structured pages/sections.
        Returns list of dicts: [{'section': '...', 'text': '...'}]
        """
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return DocumentParser._parse_pdf(file_path)
        elif suffix in (".md", ".txt"):
            return DocumentParser._parse_markdown_text(file_path)
        elif suffix == ".csv":
            return DocumentParser._parse_csv(file_path)
        elif suffix == ".json":
            return DocumentParser._parse_json(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return [{"section": "Document Body", "text": text}]

    @staticmethod
    def _parse_pdf(file_path: Path) -> List[Dict[str, Any]]:
        results = []
        try:
            reader = PdfReader(str(file_path))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    results.append({"section": f"Page {i+1}", "text": text.strip()})
        except Exception as e:
            results.append({"section": "Error", "text": f"PDF parse error: {str(e)}"})
        return results

    @staticmethod
    def _parse_markdown_text(file_path: Path) -> List[Dict[str, Any]]:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        sections = []
        current_section = "Overview"
        current_lines: List[str] = []

        for line in content.splitlines():
            if line.startswith("#"):
                if current_lines:
                    sections.append({
                        "section": current_section,
                        "text": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_section = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "section": current_section,
                "text": "\n".join(current_lines).strip()
            })
        return [s for s in sections if s["text"]]

    @staticmethod
    def _parse_csv(file_path: Path) -> List[Dict[str, Any]]:
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = None
            for idx, row in enumerate(reader):
                if idx == 0:
                    header = row
                    continue
                row_str = " | ".join(row)
                rows.append({"section": f"Row {idx}", "text": row_str})
        return rows

    @staticmethod
    def _parse_json(file_path: Path) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)

        if isinstance(data, list):
            sections = []
            for i, item in enumerate(data):
                sec_name = item.get("topic") or item.get("question") or f"Item {i+1}"
                txt = json.dumps(item, indent=2)
                sections.append({"section": str(sec_name), "text": txt})
            return sections
        elif isinstance(data, dict):
            return [{"section": k, "text": json.dumps(v, indent=2)} for k, v in data.items()]
        return [{"section": "JSON Content", "text": json.dumps(data, indent=2)}]
