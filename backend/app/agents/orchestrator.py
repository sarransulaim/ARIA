import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import BaseAgent
from app.agents.schema_agent import SchemaAgent
from app.agents.sql_agent import SQLAgent
from app.analysis.statistics import StatisticsEngine
from app.analysis.viz_recommender import VizRecommender
from app.connectors.registry import get_connector
from app.core.config import settings
from app.core.exceptions import ConnectionNotFoundError, SessionNotFoundError
from app.core.redis_client import CacheClient, RedisKeys
from app.models.db.models import (
    BusinessContext,
    DataConnection,
    QueryExecution,
    Session as SessionModel,
    Visualization,
)
from app.services.session_service import SessionService
from app.utils.encryption import decrypt

_INTENT_SYSTEM = """\
You are a senior data analyst decomposing an analytical question into an execution plan.

Given the question and database schema, output ONLY a valid JSON object — no markdown, no backticks:
{
  "intent": "trend_analysis|comparison|ranking|distribution|correlation|summary|segmentation|custom",
  "analysis_title": "Descriptive title under 60 characters",
  "complexity": "simple|moderate|complex",
  "steps": [
    {
      "step": 1,
      "purpose": "What this step answers (one sentence)",
      "sql_hint": "SQL approach: e.g. GROUP BY agent_type, compute AVG(latency_ms) and COUNT(*)",
      "uses_previous": false
    }
  ]
}

Planning rules:
- Simple lookup/aggregation → 1 step
- Ranked comparison with secondary metric → 2 steps
- Cohort, funnel, multi-metric comparison → 3 steps maximum
- Never plan more than 4 steps; prefer CTEs over multiple queries
- uses_previous=true means this step may reference results from the prior step
"""


@dataclass
class PlanStep:
    step: int
    purpose: str
    sql_hint: str
    uses_previous: bool = False


@dataclass
class StepResult:
    step: int
    sql: str
    explanation: str
    columns: List[str]
    rows: List[List]
    row_count: int
    execution_time_ms: int


@dataclass
class AnalysisState:
    session_id: uuid.UUID
    connection_id: uuid.UUID
    question: str
    intent: str = ""
    analysis_title: str = ""
    plan: List[PlanStep] = field(default_factory=list)
    schema_context: str = ""
    business_context: str = ""
    step_results: List[StepResult] = field(default_factory=list)
    combined_df: Optional[pd.DataFrame] = None
    statistics: Dict[str, Any] = field(default_factory=dict)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    narrative: str = ""
    key_insights: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    followups: List[str] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)
    query_execution_ids: List[str] = field(default_factory=list)
    error: Optional[str] = None


class OrchestratorAgent(BaseAgent):
    def __init__(self, db: AsyncSession, cache: Optional[CacheClient] = None):
        super().__init__(db=db, model=None)
        self.model = self.model_smart
        self.cache = cache

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run(self, input: dict, session_context: dict) -> dict:
        """Backward-compatible sync interface — collects the final stream event."""
        question: str = input["question"]
        session_id = uuid.UUID(str(input["session_id"]))
        connection_id = uuid.UUID(str(input["connection_id"]))
        try:
            async for event in self.stream(question, session_id, connection_id):
                if event["type"] in ("done", "error"):
                    return event.get("response", self._error_response(
                        event.get("message", "Unknown error")
                    ))
            return self._error_response("Pipeline completed without a final response.")
        except (SessionNotFoundError, ConnectionNotFoundError) as exc:
            return self._error_response(str(exc))
        except Exception as exc:
            return self._error_response(str(exc))

    async def stream(
        self,
        question: str,
        session_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Full streaming pipeline — yields SSE-ready event dicts."""
        state = AnalysisState(
            session_id=session_id,
            connection_id=connection_id,
            question=question,
        )
        try:
            async for event in self._pipeline(state):
                yield event
        except Exception as exc:
            yield {
                "type": "error",
                "message": str(exc),
                "response": self._error_response(str(exc)),
            }

    # ── Pipeline ───────────────────────────────────────────────────────────────

    async def _pipeline(self, state: AnalysisState) -> AsyncGenerator[Dict[str, Any], None]:
        # 1 ── Setup ──────────────────────────────────────────────────────────
        yield _progress("setup", "Loading session context…", 5)
        session = await self._load_session(state.session_id)
        data_conn = await self._load_connection(state.connection_id)
        credentials = json.loads(decrypt(data_conn.credentials_encrypted))
        connector = get_connector(
            data_conn.connector_type, data_conn.connection_config, credentials
        )
        session_svc = SessionService(self.db)
        ctx: Dict[str, Any] = {
            "session_id": str(state.session_id),
            "summary": session.session_summary or "",
        }

        # 2 ── Persist user message ────────────────────────────────────────────
        user_msg = await session_svc.add_message(
            session_id=state.session_id,
            role="user",
            message_type="question",
            content=state.question,
            metadata={"connection_id": str(state.connection_id)},
        )

        # 3 ── Schema context ──────────────────────────────────────────────────
        yield _progress("schema", "Identifying relevant tables…", 10)
        schema_agent = SchemaAgent(db=self.db, cache=self.cache)
        try:
            schema_result = await schema_agent.run(
                input={"question": state.question, "connection_id": state.connection_id},
                session_context=ctx,
            )
            state.schema_context = schema_result["relevant_tables_context"]
        except Exception:
            state.schema_context = "Schema context unavailable."

        # 4 ── Business context ────────────────────────────────────────────────
        state.business_context = await self._load_business_context(state.connection_id)

        # 5 ── Intent + plan ───────────────────────────────────────────────────
        yield _progress("planning", "Planning analysis approach…", 15)
        plan_data = await self._parse_intent(state, ctx)
        state.intent = plan_data.get("intent", "summary")
        state.analysis_title = plan_data.get("analysis_title", state.question[:60])
        raw_steps = plan_data.get("steps") or [
            {"step": 1, "purpose": state.question, "sql_hint": "", "uses_previous": False}
        ]
        state.plan = [
            PlanStep(
                step=s.get("step", i + 1),
                purpose=s.get("purpose", ""),
                sql_hint=s.get("sql_hint", ""),
                uses_previous=bool(s.get("uses_previous", False)),
            )
            for i, s in enumerate(raw_steps)
        ]

        yield {
            "type": "plan",
            "intent": state.intent,
            "title": state.analysis_title,
            "steps": [
                {"step": p.step, "purpose": p.purpose, "sql_hint": p.sql_hint}
                for p in state.plan
            ],
        }

        # 6 ── SQL steps ───────────────────────────────────────────────────────
        sql_agent = SQLAgent(db=self.db)
        n_steps = len(state.plan)

        for i, plan_step in enumerate(state.plan):
            pct = 20 + int((i / n_steps) * 45)
            yield _progress(
                f"sql_{plan_step.step}",
                f"Generating SQL — step {plan_step.step}: {plan_step.purpose}",
                pct,
            )

            prior_ctx = ""
            if plan_step.uses_previous and state.step_results:
                prev = state.step_results[-1]
                header = " | ".join(prev.columns[:10])
                sample = "\n".join(
                    " | ".join(str(v) for v in r[:10])
                    for r in prev.rows[:5]
                )
                prior_ctx = f"\nPrevious step result sample:\n{header}\n{sample}"

            last_error: Optional[str] = None
            step_result: Optional[StepResult] = None

            for attempt in range(settings.sql_agent_max_retries):
                qexec: Optional[QueryExecution] = None
                try:
                    sql_result = await sql_agent.run(
                        {
                            "question": state.question,
                            "step_purpose": plan_step.purpose,
                            "step_hint": (plan_step.sql_hint or "") + prior_ctx,
                            "schema_context": state.schema_context,
                            "db_dialect": connector.get_dialect(),
                            "business_context": state.business_context,
                            "session_history_summary": session.session_summary or "",
                            "is_multi_step": n_steps > 1,
                            "total_steps": n_steps,
                            "current_step": plan_step.step,
                            **({"last_error": last_error} if last_error else {}),
                        },
                        ctx,
                    )

                    qexec = QueryExecution(
                        session_id=state.session_id,
                        connection_id=state.connection_id,
                        sql_text=sql_result["sql"],
                        natural_language_prompt=f"[Step {plan_step.step}] {state.question}",
                        status="running",
                    )
                    self.db.add(qexec)
                    await self.db.flush()
                    await self.db.refresh(qexec)

                    exec_result = await connector.execute_query(sql_result["sql"])

                    qexec.status = "completed"
                    qexec.execution_time_ms = exec_result["execution_time_ms"]
                    qexec.row_count = exec_result["row_count"]
                    qexec.result_preview = {
                        "columns": exec_result["columns"],
                        "rows": exec_result["rows"][:100],
                    }
                    await self.db.flush()
                    state.query_execution_ids.append(str(qexec.id))

                    step_result = StepResult(
                        step=plan_step.step,
                        sql=sql_result["sql"],
                        explanation=sql_result.get("explanation", ""),
                        columns=exec_result["columns"],
                        rows=exec_result["rows"],
                        row_count=exec_result["row_count"],
                        execution_time_ms=exec_result["execution_time_ms"],
                    )
                    state.step_results.append(step_result)

                    yield {
                        "type": "sql",
                        "step": plan_step.step,
                        "sql": sql_result["sql"],
                        "explanation": sql_result.get("explanation", ""),
                        "tables_used": sql_result.get("tables_used", []),
                    }
                    yield {
                        "type": "result",
                        "step": plan_step.step,
                        "columns": exec_result["columns"],
                        "rows": exec_result["rows"][:100],
                        "row_count": exec_result["row_count"],
                        "execution_time_ms": exec_result["execution_time_ms"],
                    }
                    break

                except Exception as exc:
                    last_error = str(exc)
                    if qexec is not None:
                        qexec.status = "failed"
                        qexec.error_message = last_error
                        await self.db.flush()
                    if attempt == settings.sql_agent_max_retries - 1:
                        state.error = (
                            f"Step {plan_step.step} failed after "
                            f"{settings.sql_agent_max_retries} attempts: {last_error}"
                        )

            if not step_result and i == 0:
                resp = self._error_response(state.error or "SQL execution failed.")
                yield {"type": "error", "message": state.error, "response": resp}
                return

        if not state.step_results:
            resp = self._error_response("No query results obtained.")
            yield {"type": "error", "message": "No query results", "response": resp}
            return

        primary = state.step_results[0]

        # 7 ── Statistics ──────────────────────────────────────────────────────
        yield _progress("statistics", "Computing statistical analysis…", 70)
        try:
            df = StatisticsEngine.build_dataframe(primary.columns, primary.rows)
            state.combined_df = df
            state.statistics = StatisticsEngine.auto_analyze(df, state.intent)
        except Exception:
            state.statistics = {}

        if state.statistics:
            yield {"type": "stats", "data": state.statistics}

        # 8 ── Visualizations ──────────────────────────────────────────────────
        yield _progress("visualizations", "Selecting optimal visualizations…", 75)
        try:
            if state.combined_df is not None:
                state.charts = VizRecommender.recommend(state.combined_df, state.intent)
        except Exception:
            state.charts = []

        if state.charts:
            yield {"type": "visualizations", "charts": state.charts}

        # 9 ── Analyst narrative ───────────────────────────────────────────────
        yield _progress("narrative", "Writing analysis narrative…", 80)
        analyst = AnalystAgent(db=self.db)
        try:
            analysis = await analyst.run(
                {
                    "question": state.question,
                    "intent": state.intent,
                    "step_results": [
                        {
                            "step": r.step,
                            "sql": r.sql,
                            "explanation": r.explanation,
                            "columns": r.columns,
                            "rows": r.rows[:50],
                            "row_count": r.row_count,
                        }
                        for r in state.step_results
                    ],
                    "statistics": state.statistics,
                    "business_context": state.business_context,
                    "session_summary": session.session_summary or "",
                    "row_count": primary.row_count,
                },
                ctx,
            )
        except Exception:
            analysis = {
                "narrative": f"Query returned {primary.row_count} rows.",
                "key_insights": [],
                "anomalies": [],
                "hypotheses": [],
                "suggested_followups": [],
                "confidence": "low",
                "updated_summary": session.session_summary or "",
                "analysis_type": state.intent,
                "key_insight": "",
                "chart_recommended": False,
                "chart_type": "none",
                "chart_config": {},
            }

        state.narrative = analysis.get("narrative", "")
        state.key_insights = analysis.get("key_insights", [])
        state.anomalies = analysis.get("anomalies", [])
        state.followups = analysis.get("suggested_followups", [])

        yield {
            "type": "narrative",
            "narrative": state.narrative,
            "key_insights": state.key_insights,
            "anomalies": state.anomalies,
            "hypotheses": analysis.get("hypotheses", []),
        }

        # 10 ── Persist messages ───────────────────────────────────────────────
        yield _progress("persisting", "Saving results…", 90)

        last_sql_msg_id = user_msg.id
        for sr in state.step_results:
            exec_id = (
                state.query_execution_ids[sr.step - 1]
                if sr.step <= len(state.query_execution_ids)
                else None
            )
            sql_msg = await session_svc.add_message(
                session_id=state.session_id,
                role="assistant",
                message_type="sql",
                content=sr.sql,
                metadata={
                    "step": sr.step,
                    "explanation": sr.explanation,
                    "query_execution_id": exec_id,
                },
                parent_message_id=user_msg.id,
            )
            last_sql_msg_id = sql_msg.id

        result_msg = await session_svc.add_message(
            session_id=state.session_id,
            role="assistant",
            message_type="result",
            content=json.dumps({
                "columns": primary.columns,
                "rows": primary.rows[:10],
                "row_count": primary.row_count,
            }),
            metadata={"execution_time_ms": primary.execution_time_ms},
            parent_message_id=last_sql_msg_id,
        )

        analysis_msg = await session_svc.add_message(
            session_id=state.session_id,
            role="assistant",
            message_type="analysis",
            content=state.narrative,
            metadata={
                "key_insights": state.key_insights,
                "anomalies": state.anomalies,
                "suggested_followups": state.followups,
                "confidence": analysis.get("confidence", "medium"),
            },
            parent_message_id=result_msg.id,
        )

        await session_svc.update_summary(
            session_id=state.session_id,
            summary=analysis.get("updated_summary") or session.session_summary or "",
            findings=state.key_insights[:3],
        )

        if self.cache:
            try:
                await self.cache.delete(RedisKeys.session_context(str(state.session_id)))
            except Exception:
                pass

        # Persist chart visualizations (not stat_cards)
        for chart in state.charts:
            if chart.get("type") == "stat_card":
                continue
            exec_id = uuid.UUID(state.query_execution_ids[0]) if state.query_execution_ids else None
            viz = Visualization(
                session_id=state.session_id,
                query_execution_id=exec_id,
                chart_type=chart["type"],
                title=chart.get("title", state.analysis_title)[:255],
                chart_config={k: v for k, v in chart.items() if k != "data"},
            )
            self.db.add(viz)
        if state.charts:
            await self.db.flush()

        # 11 ── Build artifacts ────────────────────────────────────────────────
        artifacts = []
        if len(state.plan) > 1:
            artifacts.append({
                "artifact_type": "query_plan",
                "title": "Analysis Plan",
                "data": {
                    "intent": state.intent,
                    "title": state.analysis_title,
                    "steps": [{"step": p.step, "purpose": p.purpose} for p in state.plan],
                },
            })

        for sr in state.step_results:
            purpose = (
                state.plan[sr.step - 1].purpose
                if sr.step <= len(state.plan)
                else f"Step {sr.step}"
            )
            artifacts.append({
                "artifact_type": "sql",
                "title": f"Step {sr.step}: {purpose}",
                "data": {"sql": sr.sql, "explanation": sr.explanation, "step": sr.step},
            })
            artifacts.append({
                "artifact_type": "table",
                "title": f"Results — Step {sr.step}",
                "data": {
                    "columns": sr.columns,
                    "rows": sr.rows[:100],
                    "row_count": sr.row_count,
                    "execution_time_ms": sr.execution_time_ms,
                },
            })

        if state.statistics:
            artifacts.append({
                "artifact_type": "statistics",
                "title": "Statistical Analysis",
                "data": state.statistics,
            })

        for chart in state.charts:
            if chart.get("type") == "stat_card":
                artifacts.append({
                    "artifact_type": "stat_card",
                    "title": chart.get("title", ""),
                    "data": chart.get("data", {}),
                })
            else:
                artifacts.append({
                    "artifact_type": "chart",
                    "title": chart.get("title", ""),
                    "data": chart,
                })

        if state.key_insights:
            artifacts.append({
                "artifact_type": "insights",
                "title": "Key Insights",
                "data": {"insights": state.key_insights, "anomalies": state.anomalies},
            })

        # 12 ── Final response ─────────────────────────────────────────────────
        yield _progress("done", "Analysis complete.", 100)

        response = {
            "message_id": str(analysis_msg.id),
            "sql_generated": primary.sql,
            "sql_explanation": primary.explanation,
            "results_preview": {"columns": primary.columns, "rows": primary.rows[:10]},
            "row_count": primary.row_count,
            "analysis_narrative": state.narrative,
            "suggested_followups": state.followups,
            "visualization_config": next(
                (c for c in state.charts if c.get("type") != "stat_card"), None
            ),
            "error": False,
            # Rich fields
            "analysis_type": state.intent,
            "analysis_title": state.analysis_title,
            "artifacts": artifacts,
            "key_insights": state.key_insights,
            "statistical_summary": state.statistics,
            "data_quality_warnings": state.data_quality_warnings,
            "query_plan": [p.purpose for p in state.plan],
            "all_charts": state.charts,
            "all_step_results": [
                {
                    "step": r.step,
                    "sql": r.sql,
                    "explanation": r.explanation,
                    "columns": r.columns,
                    "rows": r.rows[:100],
                    "row_count": r.row_count,
                    "execution_time_ms": r.execution_time_ms,
                }
                for r in state.step_results
            ],
        }

        yield {"type": "done", "response": response}

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _parse_intent(self, state: AnalysisState, ctx: dict) -> Dict[str, Any]:
        session_id_raw = ctx.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None
        prompt = (
            f"Question: {state.question}\n\n"
            f"Database Schema (summary):\n{state.schema_context[:3000]}"
        )
        try:
            raw = await self._call_llm(
                messages=[{"role": "user", "content": prompt}],
                system=_INTENT_SYSTEM,
                session_id=session_id,
            )
            cleaned = re.sub(r"```(?:json)?\s*", "", raw.strip()).strip().rstrip("`")
            return json.loads(cleaned)
        except Exception:
            return {
                "intent": "summary",
                "analysis_title": state.question[:60],
                "complexity": "simple",
                "steps": [
                    {"step": 1, "purpose": state.question, "sql_hint": "", "uses_previous": False}
                ],
            }

    async def _load_session(self, session_id: uuid.UUID) -> SessionModel:
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise SessionNotFoundError(str(session_id))
        return session

    async def _load_connection(self, connection_id: uuid.UUID) -> DataConnection:
        result = await self.db.execute(
            select(DataConnection).where(DataConnection.id == connection_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise ConnectionNotFoundError(str(connection_id))
        return conn

    async def _load_business_context(self, connection_id: uuid.UUID) -> str:
        result = await self.db.execute(
            select(BusinessContext).where(BusinessContext.connection_id == connection_id)
        )
        items = result.scalars().all()
        if not items:
            return ""
        return "\n".join(f"{item.key}: {item.value}" for item in items)

    @staticmethod
    def _error_response(message: str) -> dict:
        return {
            "message_id": None,
            "sql_generated": None,
            "sql_explanation": None,
            "results_preview": None,
            "row_count": 0,
            "analysis_narrative": message,
            "suggested_followups": [
                "Can you rephrase your question?",
                "Can you describe what data you are looking for?",
            ],
            "visualization_config": None,
            "error": True,
            "analysis_type": None,
            "analysis_title": None,
            "artifacts": [],
            "key_insights": [],
            "statistical_summary": None,
            "data_quality_warnings": [],
            "query_plan": [],
            "all_charts": [],
            "all_step_results": [],
        }


def _progress(step: str, message: str, pct: int) -> Dict[str, Any]:
    return {"type": "progress", "step": step, "message": message, "pct": pct}
