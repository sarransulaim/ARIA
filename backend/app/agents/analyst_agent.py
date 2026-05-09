import json
import re
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent

_SYSTEM_PROMPT = """You are a senior data analyst interpreting SQL query results for a business audience.

Analyze the results and respond with ONLY a valid JSON object — no markdown, no backticks:
{
  "narrative": "Clear, business-focused explanation of what the data shows (2-4 sentences)",
  "key_insight": "The single most important finding in one sentence",
  "anomalies": ["any unusual pattern, outlier, or data quality issue"],
  "suggested_followups": ["follow-up question 1", "follow-up question 2", "follow-up question 3"],
  "confidence": "high|medium|low",
  "updated_summary": "Updated one-paragraph summary of this entire analysis session so far",
  "chart_recommended": true,
  "chart_type": "bar|line|pie|scatter|table|none",
  "chart_config": {
    "title": "Chart title",
    "x_axis": "column name for x axis",
    "y_axis": "column name for y axis",
    "color_by": "optional grouping column"
  }
}"""


class AnalystAgent(BaseAgent):
    """
    Interprets query results and produces business narrative, insights, and chart recommendations.
    Uses claude-sonnet-4-6 for deep reasoning.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=None)
        self.model = self.model_smart

    async def run(self, input: dict, session_context: dict) -> dict:
        question: str = input["question"]
        sql: str = input["sql"]
        query_results: Dict[str, Any] = input.get("query_results", {})
        row_count: int = input.get("row_count", 0)
        business_context: str = input.get("business_context", "")
        session_summary: str = input.get("session_summary", "")

        session_id_raw = session_context.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None

        columns = query_results.get("columns", [])
        rows = query_results.get("rows", [])
        preview_rows = rows[:50]

        results_text = self._format_results(columns, preview_rows, row_count)

        parts = [
            f"The analyst asked: {question}",
            f"\nSQL Executed:\n{sql}",
            f"\n{results_text}",
        ]
        if business_context:
            parts.append(f"\nBusiness Context:\n{business_context}")
        if session_summary:
            parts.append(f"\nSession Summary So Far:\n{session_summary}")

        raw = await self._call_llm(
            messages=[{"role": "user", "content": "\n".join(parts)}],
            system=_SYSTEM_PROMPT,
            session_id=session_id,
        )

        return self._parse_response(raw, session_summary)

    @staticmethod
    def _format_results(columns: list, rows: list, total_rows: int) -> str:
        if not columns:
            return f"Query returned {total_rows} rows with no columns."
        header = " | ".join(str(c) for c in columns)
        separator = "-" * len(header)
        row_lines = [" | ".join(str(v) for v in row) for row in rows[:20]]
        shown = len(row_lines)
        body = "\n".join(row_lines)
        note = f"\n... ({total_rows - shown} more rows not shown)" if total_rows > shown else ""
        return f"Results ({total_rows} total rows):\n{header}\n{separator}\n{body}{note}"

    @staticmethod
    def _parse_response(raw: str, fallback_summary: str) -> dict:
        cleaned = raw.strip()
        cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("`")
        try:
            parsed = json.loads(cleaned)
            # Ensure required keys exist
            parsed.setdefault("narrative", cleaned)
            parsed.setdefault("key_insight", "")
            parsed.setdefault("anomalies", [])
            parsed.setdefault("suggested_followups", [])
            parsed.setdefault("confidence", "medium")
            parsed.setdefault("updated_summary", fallback_summary)
            parsed.setdefault("chart_recommended", False)
            parsed.setdefault("chart_type", "none")
            parsed.setdefault("chart_config", {})
            return parsed
        except json.JSONDecodeError:
            return {
                "narrative": raw,
                "key_insight": "",
                "anomalies": [],
                "suggested_followups": [],
                "confidence": "medium",
                "updated_summary": fallback_summary,
                "chart_recommended": False,
                "chart_type": "none",
                "chart_config": {},
            }
