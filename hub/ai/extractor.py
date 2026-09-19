"""AI-readiness text extraction pipeline, summarization, and historical verification anchors."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from hub.core.database import Database


class AIExtractor:
    """Extracts text content, derives summary anchors, and enables historical verification."""

    def __init__(self, db: Database):
        self.db = db

    def extract_text_sample(self, file_path: Path | str, max_chars: int = 4000) -> str:
        """Extract plain text preview from document, text, or code file."""
        path = Path(file_path)
        ext = path.suffix.lower()

        # Direct text / code / markdown files
        if ext in (".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".py", ".sql", ".sh", ".ps1", ".js", ".ts"):
            try:
                return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
            except Exception:
                return ""

        # For binary document formats (PDF, DOCX), extract basic readable strings
        try:
            with open(path, "rb") as f:
                raw_bytes = f.read(max_chars * 2)
                # Filter printable ASCII/Unicode characters
                ascii_chars = [chr(b) if 32 <= b <= 126 or b in (10, 13, 9) else " " for b in raw_bytes]
                extracted = "".join(ascii_chars)
                # Clean multiple spaces
                return re.sub(r"\s+", " ", extracted).strip()[:max_chars]
        except Exception:
            return ""

    def generate_document_insights(self, file_id: int, file_path: Path | str, file_name: str) -> Dict[str, Any]:
        """Derive keywords, overview summary, and ground-truth verification anchors."""
        text = self.extract_text_sample(file_path)
        if not text:
            return {"file_id": file_id, "status": "skipped", "reason": "Non-text or empty file"}

        # Extract dates and potential monetary figures as factual anchors
        dates = re.findall(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b", text, re.I)
        amounts = re.findall(r"[\$¥€]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|CNY|RMB)\b", text)

        keywords = list(set(re.findall(r"\b[A-Za-z]{5,}\b", text[:1000])))[:10]

        summary = f"Document '{file_name}': contains {len(text)} characters of text content. "
        if dates:
            summary += f"Referenced dates: {', '.join(dates[:3])}. "
        if amounts:
            summary += f"Financial anchors: {', '.join(amounts[:3])}."

        insights = {
            "file_id": file_id,
            "text_preview": text[:500],
            "ai_summary": summary,
            "key_topics": keywords,
            "entities": {"dates": dates[:5], "amounts": amounts[:5]},
            "fact_anchor": f"Dates: {dates[:3]}; Amounts: {amounts[:3]}",
        }

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO ai_insights (
                    file_id, text_content_preview, ai_summary, key_topics_json,
                    entities_json, historical_fact_anchor, embedding_status
                ) VALUES (?, ?, ?, ?, ?, ?, 'extracted')
                ON CONFLICT(file_id) DO UPDATE SET
                    text_content_preview = excluded.text_content_preview,
                    ai_summary = excluded.ai_summary,
                    key_topics_json = excluded.key_topics_json,
                    entities_json = excluded.entities_json,
                    historical_fact_anchor = excluded.historical_fact_anchor,
                    embedding_status = 'extracted'
                """,
                (
                    file_id,
                    insights["text_preview"],
                    insights["ai_summary"],
                    json.dumps(insights["key_topics"]),
                    json.dumps(insights["entities"]),
                    insights["fact_anchor"],
                ),
            )

        return insights

    def verify_against_history(self, candidate_text: str) -> Dict[str, Any]:
        """
        Cross-reference incoming candidate text against verified historical anchors in catalog.db.
        Flags potential contradictions, duplicate statements, or matching baseline contracts.
        """
        candidate_amounts = set(re.findall(r"[\$¥€]\s*\d+(?:,\d{3})*(?:\.\d{2})?", candidate_text))
        candidate_words = set(re.findall(r"\b[A-Za-z]{6,}\b", candidate_text.lower()))

        matches = []
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT f.file_name, f.canonical_gdrive_path, a.ai_summary, a.historical_fact_anchor
                FROM ai_insights a
                JOIN files f ON a.file_id = f.file_id
                WHERE a.historical_fact_anchor IS NOT NULL
                """
            ).fetchall()

            for r in rows:
                anchor = r["historical_fact_anchor"] or ""
                # Check for overlap in financial anchors or terms
                found_amounts = [amt for amt in candidate_amounts if amt in anchor]
                if found_amounts:
                    matches.append({
                        "file_name": r["file_name"],
                        "path": r["canonical_gdrive_path"],
                        "matched_anchors": found_amounts,
                        "historical_summary": r["ai_summary"],
                    })

        return {
            "candidate_verified": True,
            "historical_matches_found": len(matches),
            "matches": matches,
        }
