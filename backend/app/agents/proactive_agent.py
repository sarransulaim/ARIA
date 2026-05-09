import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.exceptions import SessionNotFoundError
from app.models.db.models import Message, QueryExecution, Session as SessionModel

_SYSTEM_PROMPT = """You are a proactive data analyst assistant.
Given an analysis session's recent activity, identify important patterns, anomalies, or opportunities
the analyst has NOT yet asked about. Your job is to surface insights they would want to know.

Respond with ONLY a valid JSON object — no markdown, no backticks:
{
  "insights": [
    {
      "title": "Short, specific insight title",
      "narrative": "2-3 sentence explanation of what you found and why it matters",
      "suggested_question": "A specific follow-up question the analyst should ask",
      "priority": "high|medium|low",
      "data_reference": "Which query/result prompted this insight"
    }
  ]
}

Rules:
- Produce 2-4 insights maximum
- Only surface insights NOT already covered by the existing key_findings
- Priority 'high' = anomaly or urgent issue; 'medium' = meaningful pattern; 'low' = interesting but not urgent
- Each insight must reference specific numbers, tables, or patterns from the session data
- If there is nothing noteworthy to surface, return {"insights": []}"""


class ProactiveAgent(BaseAgent):
    """
    Scans session data in the background and surfaces unsolicited insights.
    Only runs when settings.feature_proactive_agent is True.
    Uses claude-haiku-4-5-20251001 for cost efficiency (background task).
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=None)
        self.model = self.model_fast

    async def run(self, input: dict, session_context: dict) -> dict:
        session_id = uuid.UUID(str(input["session_id"]))

        session_data = await self._load_session_data(session_id)
        if not session_data["has_data"]:
            return {"insights": [], "session_id": str(session_id)}

        user_content = self._build_prompt(session_data)
        raw = await self._call_llm(
            messages=[{"role": "user", "content": user_content}],
            system=_SYSTEM_PROMPT,
            session_id=session_id,
        )

        insights = self._parse_insights(raw)
        new_findings = [i["title"] for i in insights if i.get("priority") in ("high", "medium")]

        if new_findings:
            await self._append_findings(session_id, session_data["existing_findings"], new_findings)
            await self._persist_insight_messages(session_id, insights)

        return {"insights": insights, "session_id": str(session_id)}

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _load_session_data(self, session_id: uuid.UUID) -> Dict[str, Any]:
        s_result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = s_result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError(str(session_id))

        qe_result = await self.db.execute(
            select(QueryExecution)
            .where(
                QueryExecution.session_id == session_id,
                QueryExecution.status == "completed",
            )
            .order_by(QueryExecution.created_at.desc())
            .limit(10)
        )
        executions: List[QueryExecution] = list(qe_result.scalars().all())

        msg_result = await self.db.execute(
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.role == "assistant",
                Message.message_type == "analysis",
            )
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        analysis_msgs: List[Message] = list(msg_result.scalars().all())

        return {
            "title": session.title,
            "summary": session.session_summary or "",
            "existing_findings": session.key_findings or [],
            "query_count": len(executions),
            "queries": [
                {
                    "sql": qe.sql_text[:300],
                    "prompt": qe.natural_language_prompt[:200],
                    "row_count": qe.row_count,
                    "preview": (qe.result_preview or {}).get("rows", [])[:5],
                    "columns": (qe.result_preview or {}).get("columns", []),
                }
                for qe in executions
            ],
            "recent_analyses": [m.content[:400] for m in analysis_msgs],
            "has_data": len(executions) >= 2,
        }

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        queries_text = "\n".join(
            f"  Q{i+1}: '{q['prompt']}' → {q['row_count']} rows\n"
            f"       Columns: {q['columns']}\n"
            f"       Sample: {q['preview'][:3]}"
            for i, q in enumerate(data["queries"])
        )
        analyses_text = "\n".join(
            f"  A{i+1}: {a}" for i, a in enumerate(data["recent_analyses"])
        ) or "  None"
        findings_text = "\n".join(f"  - {f}" for f in data["existing_findings"]) or "  None yet"

        return (
            f"Session: {data['title']}\n"
            f"Summary: {data['summary']}\n\n"
            f"Already known findings:\n{findings_text}\n\n"
            f"Recent queries run ({data['query_count']} total):\n{queries_text}\n\n"
            f"Recent analysis narratives:\n{analyses_text}\n\n"
            "Identify 2-4 important insights NOT already covered above."
        )

    @staticmethod
    def _parse_insights(raw: str) -> List[dict]:
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        try:
            parsed = json.loads(cleaned)
            insights = parsed.get("insights", [])
            result = []
            for item in insights:
                result.append({
                    "title": item.get("title", ""),
                    "narrative": item.get("narrative", ""),
                    "suggested_question": item.get("suggested_question", ""),
                    "priority": item.get("priority", "medium"),
                    "data_reference": item.get("data_reference", ""),
                })
            return result
        except (json.JSONDecodeError, Exception):
            return []

    async def _append_findings(
        self,
        session_id: uuid.UUID,
        existing: List[str],
        new_findings: List[str],
    ) -> None:
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            combined = list(dict.fromkeys(existing + new_findings))
            session.key_findings = combined[:20]
            await self.db.flush()

    async def _persist_insight_messages(
        self,
        session_id: uuid.UUID,
        insights: List[dict],
    ) -> None:
        for insight in insights:
            msg = Message(
                session_id=session_id,
                role="assistant",
                message_type="proactive_insight",
                content=insight["narrative"],
                msg_metadata={
                    "title": insight["title"],
                    "suggested_question": insight["suggested_question"],
                    "priority": insight["priority"],
                    "data_reference": insight["data_reference"],
                },
            )
            self.db.add(msg)
        await self.db.flush()
