import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import BaseAgent
from app.agents.schema_agent import SchemaAgent
from app.agents.sql_agent import SQLAgent
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


class OrchestratorAgent(BaseAgent):
    """
    The only agent the human talks to. Coordinates the full analysis pipeline:
    SchemaAgent → SQLAgent → execute → AnalystAgent → persist → respond.
    Never exposes raw exceptions — always returns structured AnalysisResponse-shaped dicts.
    """

    def __init__(self, db: AsyncSession, cache: Optional[CacheClient] = None):
        super().__init__(db=db, model=None)
        self.model = self.model_smart
        self.cache = cache

    # ── Public entry point ─────────────────────────────────────────────────────

    async def run(self, input: dict, session_context: dict) -> dict:
        question: str = input["question"]
        session_id = uuid.UUID(str(input["session_id"]))
        connection_id = uuid.UUID(str(input["connection_id"]))

        try:
            return await self._pipeline(question, session_id, connection_id)
        except (SessionNotFoundError, ConnectionNotFoundError) as exc:
            return self._error_response(str(exc))
        except Exception:
            return self._error_response(
                "ARIA encountered an unexpected error. Please try rephrasing your question "
                "or check that the connection is active and the schema has been indexed."
            )

    # ── Private pipeline ───────────────────────────────────────────────────────

    async def _pipeline(
        self,
        question: str,
        session_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> dict:
        # 1 ── Load session & connection ──────────────────────────────────────
        session = await self._load_session(session_id)
        data_conn = await self._load_connection(connection_id)

        credentials = json.loads(decrypt(data_conn.credentials_encrypted))
        connector = get_connector(
            data_conn.connector_type, data_conn.connection_config, credentials
        )

        # 2 ── Build + cache session context ──────────────────────────────────
        ctx: Dict[str, Any] = {
            "session_id": str(session_id),
            "summary": session.session_summary or "",
            "key_findings": session.key_findings or [],
        }
        if self.cache:
            cached = await self.cache.get(RedisKeys.session_context(str(session_id)))
            if cached and isinstance(cached, dict):
                ctx.update(cached)

        # 3 ── Persist user question as message ───────────────────────────────
        session_svc = SessionService(self.db)
        user_msg = await session_svc.add_message(
            session_id=session_id,
            role="user",
            message_type="question",
            content=question,
            metadata={"connection_id": str(connection_id)},
        )

        # 4 ── Schema Agent ────────────────────────────────────────────────────
        schema_agent = SchemaAgent(db=self.db, cache=self.cache)
        try:
            schema_result = await schema_agent.run(
                input={"question": question, "connection_id": connection_id},
                session_context=ctx,
            )
        except Exception as exc:
            return self._error_response(
                f"I couldn't identify relevant tables for your question. "
                f"Make sure the schema has been indexed first. Detail: {exc}"
            )
        schema_context = schema_result["relevant_tables_context"]

        # 5 ── Business context ────────────────────────────────────────────────
        business_context = await self._load_business_context(connection_id)

        # 6 ── SQL Agent + execute (retry loop) ───────────────────────────────
        sql_agent = SQLAgent(db=self.db)
        analyst_agent = AnalystAgent(db=self.db)

        sql_result: Optional[dict] = None
        exec_result: Optional[dict] = None
        final_query_exec: Optional[QueryExecution] = None
        last_exec_error: Optional[str] = None

        for attempt in range(settings.sql_agent_max_retries):
            query_exec: Optional[QueryExecution] = None
            try:
                sql_input = {
                    "question": question,
                    "schema_context": schema_context,
                    "db_dialect": connector.get_dialect(),
                    "business_context": business_context,
                    "session_history_summary": session.session_summary or "",
                }
                if last_exec_error:
                    sql_input["last_error"] = last_exec_error

                sql_result = await sql_agent.run(sql_input, ctx)

                # Persist execution record before running (creates an audit trail)
                query_exec = QueryExecution(
                    session_id=session_id,
                    connection_id=connection_id,
                    sql_text=sql_result["sql"],
                    natural_language_prompt=question,
                    status="running",
                )
                self.db.add(query_exec)
                await self.db.flush()
                await self.db.refresh(query_exec)

                exec_result = await connector.execute_query(sql_result["sql"])

                query_exec.status = "completed"
                query_exec.execution_time_ms = exec_result["execution_time_ms"]
                query_exec.row_count = exec_result["row_count"]
                query_exec.result_preview = {
                    "columns": exec_result["columns"],
                    "rows": exec_result["rows"][:100],
                }
                await self.db.flush()
                final_query_exec = query_exec
                break  # ← success

            except Exception as exc:
                last_exec_error = str(exc)
                if query_exec is not None:
                    query_exec.status = "failed"
                    query_exec.error_message = last_exec_error
                    await self.db.flush()
                if attempt == settings.sql_agent_max_retries - 1:
                    return self._error_response(
                        f"I tried {settings.sql_agent_max_retries} times but could not run a "
                        f"valid query. Last error: {last_exec_error}"
                    )

        # 7 ── Analyst Agent ───────────────────────────────────────────────────
        try:
            analysis = await analyst_agent.run(
                input={
                    "question": question,
                    "sql": sql_result["sql"],
                    "query_results": {
                        "columns": exec_result["columns"],
                        "rows": exec_result["rows"][:50],
                    },
                    "row_count": exec_result["row_count"],
                    "business_context": business_context,
                    "session_summary": session.session_summary or "",
                },
                session_context=ctx,
            )
        except Exception:
            analysis = {
                "narrative": (
                    f"The query returned {exec_result['row_count']} row(s). "
                    "Narrative analysis is temporarily unavailable."
                ),
                "key_insight": "",
                "anomalies": [],
                "suggested_followups": [],
                "confidence": "low",
                "updated_summary": session.session_summary or "",
                "chart_recommended": False,
                "chart_type": "none",
                "chart_config": {},
            }

        # 8 ── Persist conversation messages ───────────────────────────────────
        sql_msg = await session_svc.add_message(
            session_id=session_id,
            role="assistant",
            message_type="sql",
            content=sql_result["sql"],
            metadata={
                "explanation": sql_result.get("explanation", ""),
                "tables_used": sql_result.get("tables_used", []),
                "confidence": sql_result.get("confidence", "medium"),
                "query_execution_id": str(final_query_exec.id),
            },
            parent_message_id=user_msg.id,
        )

        result_msg = await session_svc.add_message(
            session_id=session_id,
            role="assistant",
            message_type="result",
            content=json.dumps({
                "columns": exec_result["columns"],
                "rows": exec_result["rows"][:10],
                "row_count": exec_result["row_count"],
            }),
            metadata={
                "execution_time_ms": exec_result["execution_time_ms"],
                "row_count": exec_result["row_count"],
            },
            parent_message_id=sql_msg.id,
        )

        analysis_msg = await session_svc.add_message(
            session_id=session_id,
            role="assistant",
            message_type="analysis",
            content=analysis["narrative"],
            metadata={
                "key_insight": analysis.get("key_insight", ""),
                "anomalies": analysis.get("anomalies", []),
                "suggested_followups": analysis.get("suggested_followups", []),
                "confidence": analysis.get("confidence", "medium"),
                "chart_recommended": analysis.get("chart_recommended", False),
                "chart_type": analysis.get("chart_type", "none"),
            },
            parent_message_id=result_msg.id,
        )

        # 9 ── Update session summary ──────────────────────────────────────────
        await session_svc.update_summary(
            session_id=session_id,
            summary=analysis.get("updated_summary") or session.session_summary or "",
            findings=[analysis["key_insight"]] if analysis.get("key_insight") else [],
        )

        # Bust session context cache so the next request picks up fresh summary
        if self.cache:
            await self.cache.delete(RedisKeys.session_context(str(session_id)))

        # 10 ── Create visualization record if chart recommended ───────────────
        viz_config: Optional[dict] = None
        if analysis.get("chart_recommended") and analysis.get("chart_type", "none") != "none":
            viz = Visualization(
                session_id=session_id,
                query_execution_id=final_query_exec.id,
                chart_type=analysis["chart_type"],
                title=question[:255],
                chart_config=analysis.get("chart_config") or {},
            )
            self.db.add(viz)
            await self.db.flush()
            viz_config = {
                "chart_type": analysis["chart_type"],
                **(analysis.get("chart_config") or {}),
            }

        # 11 ── Build response ─────────────────────────────────────────────────
        return {
            "message_id": str(analysis_msg.id),
            "sql_generated": sql_result["sql"],
            "sql_explanation": sql_result.get("explanation", ""),
            "results_preview": {
                "columns": exec_result["columns"],
                "rows": exec_result["rows"][:10],
            },
            "row_count": exec_result["row_count"],
            "analysis_narrative": analysis["narrative"],
            "suggested_followups": analysis.get("suggested_followups", []),
            "visualization_config": viz_config,
            "error": False,
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

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
        }
