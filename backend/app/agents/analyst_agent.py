import json
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent

_SYSTEM = """\
You are a Principal Data Scientist presenting findings to a C-suite audience.

You have access to: the original question, all SQL steps executed, their results, \
and optional statistical analysis (correlations, trends, group comparisons).

Structure your response as ONLY a valid JSON object — no markdown, no backticks:
{
  "narrative": "Bottom-line-up-front executive summary (3-5 sentences). Lead with the most important finding and exact number. Explain what drives the pattern. Reference statistical evidence if provided.",
  "key_insights": [
    "Specific finding with exact number or percentage",
    "Trend or comparison with magnitude (e.g., '3.2x higher than average')",
    "Surprising or actionable finding"
  ],
  "anomalies": ["Any outlier, data quality issue, or statistical anomaly worth flagging"],
  "hypotheses": ["What might explain this pattern and why — be specific"],
  "suggested_followups": [
    "Specific analytical next-question 1",
    "Specific analytical next-question 2",
    "Specific analytical next-question 3"
  ],
  "confidence": "high|medium|low",
  "updated_summary": "One-paragraph session summary incorporating this new finding",
  "analysis_type": "trend_analysis|comparison|ranking|distribution|correlation|summary|segmentation|custom"
}

Guidelines:
- Use exact numbers (not 'many' or 'high' — say '47% higher' or '3.2x the average')
- Reference statistical evidence: correlation r=0.82, p<0.05, R²=0.91
- Flag data quality issues if sample <30 rows or has >20% nulls
- Next steps must be specific questions, not generic 'investigate further'
- Never say 'the data shows' — say what the data shows
"""


class AnalystAgent(BaseAgent):
    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=None)
        self.model = self.model_smart

    async def run(self, input: dict, session_context: dict) -> dict:
        question: str = input["question"]
        session_summary: str = input.get("session_summary", "")
        business_context: str = input.get("business_context", "")
        intent: str = input.get("intent", "")
        statistics: Dict[str, Any] = input.get("statistics", {})

        session_id_raw = session_context.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None

        # Support both old single-result and new multi-step inputs
        step_results: Optional[List[Dict]] = input.get("step_results")
        if step_results:
            results_text = self._format_step_results(step_results)
        else:
            # Legacy single-result path
            sql = input.get("sql", "")
            qr = input.get("query_results", {})
            row_count = input.get("row_count", 0)
            results_text = self._format_single_result(sql, qr, row_count)

        parts = [
            f"Question: {question}",
            results_text,
        ]
        if intent:
            parts.append(f"\nAnalysis intent: {intent}")
        if statistics:
            parts.append(f"\nStatistical analysis:\n{json.dumps(statistics, indent=2)}")
        if business_context:
            parts.append(f"\nBusiness context:\n{business_context}")
        if session_summary:
            parts.append(f"\nSession summary so far:\n{session_summary}")

        raw = await self._call_llm(
            messages=[{"role": "user", "content": "\n".join(parts)}],
            system=_SYSTEM,
            session_id=session_id,
        )

        return self._parse(raw, session_summary, intent)

    @staticmethod
    def _format_step_results(step_results: List[Dict]) -> str:
        parts = []
        for sr in step_results:
            step = sr.get("step", "?")
            sql = sr.get("sql", "")
            explanation = sr.get("explanation", "")
            columns = sr.get("columns", [])
            rows = sr.get("rows", [])
            row_count = sr.get("row_count", 0)
            header = " | ".join(str(c) for c in columns)
            row_lines = [" | ".join(str(v) for v in r) for r in rows[:20]]
            body = "\n".join(row_lines)
            note = f"\n… ({row_count - len(row_lines)} more rows)" if row_count > len(row_lines) else ""
            parts.append(
                f"\n--- Step {step}: {explanation} ---\n"
                f"SQL: {sql}\n"
                f"Results ({row_count} rows):\n{header}\n{body}{note}"
            )
        return "\n".join(parts)

    @staticmethod
    def _format_single_result(sql: str, query_results: Dict, row_count: int) -> str:
        columns = query_results.get("columns", [])
        rows = query_results.get("rows", [])
        if not columns:
            return f"SQL: {sql}\nQuery returned {row_count} rows."
        header = " | ".join(str(c) for c in columns)
        row_lines = [" | ".join(str(v) for v in r) for r in rows[:20]]
        body = "\n".join(row_lines)
        note = f"\n… ({row_count - len(row_lines)} more rows)" if row_count > len(row_lines) else ""
        return f"SQL: {sql}\nResults ({row_count} rows):\n{header}\n{body}{note}"

    @staticmethod
    def _parse(raw: str, fallback_summary: str, fallback_intent: str) -> dict:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw.strip()).strip().rstrip("`")
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "narrative": raw,
                "key_insights": [],
                "anomalies": [],
                "hypotheses": [],
                "suggested_followups": [],
                "confidence": "medium",
                "updated_summary": fallback_summary,
                "analysis_type": fallback_intent,
                # Legacy keys kept for backward compat
                "key_insight": "",
                "chart_recommended": False,
                "chart_type": "none",
                "chart_config": {},
            }
        parsed.setdefault("narrative", cleaned)
        parsed.setdefault("key_insights", [])
        parsed.setdefault("anomalies", [])
        parsed.setdefault("hypotheses", [])
        parsed.setdefault("suggested_followups", [])
        parsed.setdefault("confidence", "medium")
        parsed.setdefault("updated_summary", fallback_summary)
        parsed.setdefault("analysis_type", fallback_intent)
        # Legacy keys for backward compat
        parsed.setdefault("key_insight", parsed["key_insights"][0] if parsed["key_insights"] else "")
        parsed.setdefault("chart_recommended", False)
        parsed.setdefault("chart_type", "none")
        parsed.setdefault("chart_config", {})
        return parsed
