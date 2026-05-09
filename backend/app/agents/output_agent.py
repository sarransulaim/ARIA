import json
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.exceptions import SessionNotFoundError
from app.models.db.models import Message, Session as SessionModel, Visualization

_SYSTEM_PROMPT = """You are an expert analyst and report writer.
Given an analysis session's data, produce a comprehensive structured content plan.

Respond with ONLY a valid JSON object — no markdown, no backticks:
{
  "title": "Descriptive report/presentation title",
  "executive_summary": "2-3 sentence high-level summary of the entire analysis",
  "sections": [
    {
      "heading": "Section heading",
      "content": "2-4 paragraphs of analytical content for this section",
      "talking_points": ["key point 1", "key point 2"],
      "visualization_id": "uuid-string-of-relevant-chart-or-null"
    }
  ],
  "recommendations": [
    "Specific, actionable recommendation 1",
    "Specific, actionable recommendation 2",
    "Specific, actionable recommendation 3"
  ]
}

Rules:
- visualization_id must be one of the provided UUIDs or null
- Produce 3-6 sections covering: overview, key findings, trends/patterns, anomalies, and next steps
- recommendations must be specific and actionable
- content should reference actual numbers and findings from the session"""


class OutputAgent(BaseAgent):
    """
    Transforms a full analysis session into a structured document content plan.
    Uses claude-sonnet-4-6 to write business-quality narrative.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=None)
        self.model = self.model_smart

    async def run(self, input: dict, session_context: dict) -> dict:
        session_id = uuid.UUID(str(input["session_id"]))
        output_type: str = input.get("output_type", "report")
        audience: str = input.get("audience") or "business stakeholders"
        focus: str = input.get("focus") or "key findings and actionable recommendations"

        session_data = await self._load_session_data(session_id)

        viz_list = "\n".join(
            f"  - {v['id']}: {v['title']} ({v['chart_type']})"
            for v in session_data["visualizations"]
        ) or "  None"

        findings_text = "\n".join(
            f"  • {f}" for f in session_data["key_findings"]
        ) or "  None recorded"

        user_content = (
            f"Create a {output_type} content plan for this analysis session.\n"
            f"Target audience: {audience}\n"
            f"Focus: {focus}\n\n"
            f"Session title: {session_data['title']}\n\n"
            f"Session summary:\n{session_data['summary']}\n\n"
            f"Key findings:\n{findings_text}\n\n"
            f"Conversation highlights:\n{session_data['conversation_excerpt']}\n\n"
            f"Available visualizations (use these UUIDs in visualization_id):\n{viz_list}"
        )

        raw = await self._call_llm(
            messages=[{"role": "user", "content": user_content}],
            system=_SYSTEM_PROMPT,
            session_id=session_id,
        )

        return self._parse_plan(raw, session_data)

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _load_session_data(self, session_id: uuid.UUID) -> Dict[str, Any]:
        s_result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = s_result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError(str(session_id))

        m_result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(30)
        )
        messages: List[Message] = list(reversed(m_result.scalars().all()))

        v_result = await self.db.execute(
            select(Visualization).where(Visualization.session_id == session_id)
        )
        visualizations = v_result.scalars().all()

        # Build a readable conversation excerpt
        conv_lines: List[str] = []
        for msg in messages:
            if msg.role == "user":
                conv_lines.append(f"Q: {msg.content[:250]}")
            elif msg.message_type == "analysis":
                conv_lines.append(f"A: {msg.content[:350]}")
            elif msg.message_type == "sql":
                conv_lines.append(f"SQL: {msg.content[:200]}")

        return {
            "title": session.title,
            "summary": session.session_summary or "No summary recorded yet.",
            "key_findings": session.key_findings or [],
            "conversation_excerpt": "\n".join(conv_lines[-12:]) or "No conversation history.",
            "visualizations": [
                {
                    "id": str(v.id),
                    "title": v.title or "Untitled Chart",
                    "chart_type": v.chart_type,
                    "chart_config": v.chart_config or {},
                }
                for v in visualizations
            ],
        }

    @staticmethod
    def _parse_plan(raw: str, session_data: Dict[str, Any]) -> dict:
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        try:
            plan = json.loads(cleaned)
        except json.JSONDecodeError:
            # Graceful fallback: wrap raw text as a single-section plan
            plan = {
                "title": session_data["title"] or "Analysis Report",
                "executive_summary": session_data["summary"],
                "sections": [
                    {
                        "heading": "Analysis Overview",
                        "content": raw[:2000],
                        "talking_points": [],
                        "visualization_id": None,
                    }
                ],
                "recommendations": [],
            }

        plan.setdefault("title", session_data["title"] or "Analysis Report")
        plan.setdefault("executive_summary", session_data["summary"])
        plan.setdefault("sections", [])
        plan.setdefault("recommendations", [])

        # Validate visualization_id values — only keep real IDs
        valid_ids = {v["id"] for v in session_data["visualizations"]}
        for section in plan["sections"]:
            section.setdefault("heading", "")
            section.setdefault("content", "")
            section.setdefault("talking_points", [])
            viz_id = section.get("visualization_id")
            if viz_id and viz_id not in valid_ids:
                section["visualization_id"] = None

        return plan
