import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import anthropic
import openai
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector
from app.core.config import settings
from app.core.redis_client import CacheClient, RedisKeys
from app.models.db.models import AgentLog, DataConnection, SchemaColumn, SchemaTable


class SchemaBrain:
    """
    Responsible for indexing a database schema into pgvector and answering
    "which tables are relevant to this question?" via cosine similarity search.
    """

    def __init__(
        self,
        connection_id: uuid.UUID,
        db: AsyncSession,
        connector: Optional[BaseConnector] = None,
        cache: Optional[CacheClient] = None,
    ):
        self.connection_id = connection_id
        self.db = db
        self.connector = connector
        self.cache = cache
        self._claude = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _embed(self, text_to_embed: str) -> List[float]:
        response = await self._openai.embeddings.create(
            model="text-embedding-3-small",
            input=text_to_embed,
            dimensions=1536,
        )
        return response.data[0].embedding

    async def _log_llm(
        self,
        *,
        agent_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
    ) -> None:
        log = AgentLog(
            session_id=session_id,
            agent_type=agent_type,
            model_used=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.flush()

    async def _describe_table(self, table_key: str, table_info: Dict[str, Any]) -> str:
        columns_text = "\n".join(
            f"  {col['column_name']} ({col['data_type']})"
            for col in table_info.get("columns", [])
        )
        prompt = (
            f"Table: {table_key}\n"
            f"Columns:\n{columns_text}\n\n"
            "Write one concise sentence describing what this database table stores "
            "and its business purpose. Be specific and factual."
        )

        start = time.monotonic()
        try:
            resp = await self._claude.messages.create(
                model=settings.anthropic_model_fast,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            description = resp.content[0].text.strip()
            await self._log_llm(
                agent_type="schema_brain",
                model=settings.anthropic_model_fast,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                latency_ms=latency_ms,
            )
            return description
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_llm(
                agent_type="schema_brain",
                model=settings.anthropic_model_fast,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(exc),
            )
            return f"Table {table_key}."

    async def _describe_column(self, table_name: str, col: Dict[str, Any]) -> str:
        is_pk = col.get("is_pk", False)
        is_fk = col.get("is_fk", False)
        prompt = (
            f"Table: {table_name}\n"
            f"Column: {col['column_name']} ({col['data_type']})"
            + (" [primary key]" if is_pk else "")
            + (" [foreign key]" if is_fk else "")
            + "\n\nWrite one concise sentence describing what this column stores."
        )

        start = time.monotonic()
        try:
            resp = await self._claude.messages.create(
                model=settings.anthropic_model_fast,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            description = resp.content[0].text.strip()
            await self._log_llm(
                agent_type="schema_brain",
                model=settings.anthropic_model_fast,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                latency_ms=latency_ms,
            )
            return description
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_llm(
                agent_type="schema_brain",
                model=settings.anthropic_model_fast,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(exc),
            )
            return f"Column {col['column_name']} in {table_name}."

    @staticmethod
    def _format_embedding(embedding: List[float]) -> str:
        """Format a float list as the pgvector literal '[x,y,...]'."""
        return "[" + ",".join(str(v) for v in embedding) + "]"

    # ── Public API ─────────────────────────────────────────────────────────────

    async def index_schema(self) -> None:
        """
        Pull the full schema from the connector, describe every table and column
        with Claude haiku, embed with OpenAI, and persist into schema_tables /
        schema_columns with their vector embeddings.
        """
        if self.connector is None:
            raise ValueError("SchemaBrain.index_schema() requires a connector")

        raw_schema: Dict[str, Any] = await self.connector.get_raw_schema()

        for table_key, table_info in raw_schema.items():
            tbl_schema = table_info["schema"]
            tbl_name = table_info["table"]
            columns_info: List[Dict[str, Any]] = table_info.get("columns", [])

            # ── Table-level description + embedding ───────────────────────────
            description = await self._describe_table(table_key, table_info)
            embed_text = f"Table {tbl_schema}.{tbl_name}: {description}"
            embedding = await self._embed(embed_text)

            # Upsert schema_tables row
            result = await self.db.execute(
                select(SchemaTable).where(
                    SchemaTable.connection_id == self.connection_id,
                    SchemaTable.table_schema == tbl_schema,
                    SchemaTable.table_name == tbl_name,
                )
            )
            schema_table = result.scalar_one_or_none()

            if schema_table is None:
                schema_table = SchemaTable(
                    connection_id=self.connection_id,
                    table_schema=tbl_schema,
                    table_name=tbl_name,
                    description=description,
                    embedding=embedding,
                )
                self.db.add(schema_table)
                await self.db.flush()
                await self.db.refresh(schema_table)
            else:
                schema_table.description = description
                schema_table.embedding = embedding
                await self.db.flush()

            # ── Column-level descriptions + embeddings ────────────────────────
            for col in columns_info:
                col_name = col["column_name"]
                # is_nullable comes from information_schema as 'YES'/'NO'
                is_nullable = col.get("is_nullable") in (True, "YES", "yes")

                col_description = await self._describe_column(tbl_name, col)
                col_embed_text = (
                    f"Column {col_name} in {tbl_schema}.{tbl_name}: {col_description}"
                )
                col_embedding = await self._embed(col_embed_text)

                result = await self.db.execute(
                    select(SchemaColumn).where(
                        SchemaColumn.table_id == schema_table.id,
                        SchemaColumn.column_name == col_name,
                    )
                )
                schema_col = result.scalar_one_or_none()

                if schema_col is None:
                    schema_col = SchemaColumn(
                        table_id=schema_table.id,
                        column_name=col_name,
                        data_type=col["data_type"],
                        is_pk=bool(col.get("is_pk", False)),
                        is_fk=bool(col.get("is_fk", False)),
                        is_nullable=is_nullable,
                        description=col_description,
                        embedding=col_embedding,
                    )
                    self.db.add(schema_col)
                else:
                    schema_col.data_type = col["data_type"]
                    schema_col.is_pk = bool(col.get("is_pk", False))
                    schema_col.is_fk = bool(col.get("is_fk", False))
                    schema_col.is_nullable = is_nullable
                    schema_col.description = col_description
                    schema_col.embedding = col_embedding

                await self.db.flush()

        # Stamp schema_last_indexed_at on the connection record
        conn_result = await self.db.execute(
            select(DataConnection).where(DataConnection.id == self.connection_id)
        )
        data_conn = conn_result.scalar_one_or_none()
        if data_conn:
            data_conn.schema_last_indexed_at = datetime.now(timezone.utc)
            await self.db.flush()

        # Bust the Redis schema cache so next read hits the DB
        if self.cache:
            await self.cache.delete(RedisKeys.schema_cache(str(self.connection_id)))

    async def find_relevant_tables(
        self, question: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Embed the question and run a pgvector cosine similarity search against
        schema_tables.embedding. Returns the top_k tables enriched with their columns.
        """
        question_embedding = await self._embed(question)
        embedding_literal = self._format_embedding(question_embedding)

        rows = (
            await self.db.execute(
                text(
                    """
                    SELECT
                        id,
                        connection_id,
                        table_schema,
                        table_name,
                        description,
                        tags,
                        created_at,
                        updated_at,
                        1 - (embedding <=> :emb::vector) AS similarity
                    FROM schema_tables
                    WHERE connection_id = :cid
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> :emb::vector
                    LIMIT :top_k
                    """
                ),
                {
                    "emb": embedding_literal,
                    "cid": str(self.connection_id),
                    "top_k": top_k,
                },
            )
        ).fetchall()

        tables: List[Dict[str, Any]] = []
        for row in rows:
            col_result = await self.db.execute(
                select(SchemaColumn).where(SchemaColumn.table_id == row.id)
            )
            columns = col_result.scalars().all()

            tables.append(
                {
                    "id": row.id,
                    "connection_id": row.connection_id,
                    "table_schema": row.table_schema,
                    "table_name": row.table_name,
                    "description": row.description,
                    "tags": row.tags or [],
                    "similarity": float(row.similarity),
                    "columns": [
                        {
                            "id": str(col.id),
                            "column_name": col.column_name,
                            "data_type": col.data_type,
                            "is_pk": col.is_pk,
                            "is_fk": col.is_fk,
                            "is_nullable": col.is_nullable,
                            "description": col.description,
                            "sample_values": col.sample_values or [],
                        }
                        for col in columns
                    ],
                }
            )

        return tables

    async def get_context_for_query(self, question: str) -> str:
        """
        Return a formatted schema context block ready to inject into an agent prompt.
        Calls find_relevant_tables internally.
        """
        tables = await self.find_relevant_tables(question)

        if not tables:
            return "No indexed schema context is available for this connection."

        lines: List[str] = ["# Relevant Database Schema\n"]
        for tbl in tables:
            lines.append(f"## {tbl['table_schema']}.{tbl['table_name']}")
            if tbl.get("description"):
                lines.append(f"Description: {tbl['description']}")
            lines.append("")
            lines.append("Columns:")
            for col in tbl.get("columns", []):
                markers = ""
                if col.get("is_pk"):
                    markers += " [PK]"
                if col.get("is_fk"):
                    markers += " [FK]"
                desc_part = f" — {col['description']}" if col.get("description") else ""
                samples = col.get("sample_values", [])
                sample_part = f" (e.g. {samples[:3]})" if samples else ""
                lines.append(
                    f"  {col['column_name']} {col['data_type']}{markers}{desc_part}{sample_part}"
                )
            lines.append("")

        return "\n".join(lines)
