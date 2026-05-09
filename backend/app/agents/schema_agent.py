import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.redis_client import CacheClient
from app.knowledge.schema_brain import SchemaBrain


class SchemaAgent(BaseAgent):
    """
    Finds schema tables relevant to the user's question.
    Uses vector similarity search (SchemaBrain) and claude-haiku to confirm relevance.
    """

    def __init__(self, db: AsyncSession, cache: Optional[CacheClient] = None):
        super().__init__(db=db, model=None)  # overridden below to haiku
        self.model = self.model_fast
        self.cache = cache

    async def run(self, input: dict, session_context: dict) -> dict:
        question: str = input["question"]
        connection_id: uuid.UUID = (
            input["connection_id"]
            if isinstance(input["connection_id"], uuid.UUID)
            else uuid.UUID(str(input["connection_id"]))
        )
        session_id_raw = session_context.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None

        brain = SchemaBrain(
            connection_id=connection_id,
            db=self.db,
            connector=None,
            cache=self.cache,
        )

        tables = await brain.find_relevant_tables(question, top_k=6)
        context_str = await brain.get_context_for_query(question)

        if not tables:
            return {
                "relevant_tables_context": "No indexed schema found for this connection.",
                "tables_found": [],
            }

        # Use Claude haiku to confirm which of the found tables are truly relevant
        table_names = [f"{t['table_schema']}.{t['table_name']}" for t in tables]
        system = (
            "You are a schema-routing assistant. Given a user question and candidate tables, "
            "identify which tables are needed to answer the question. "
            "Respond with ONLY a JSON array of the relevant table names, e.g. [\"public.orders\", \"public.customers\"]. "
            "Include only tables truly needed. No other text."
        )
        user_content = (
            f"Question: {question}\n\n"
            f"Candidate tables: {table_names}\n\n"
            f"Schema details:\n{context_str}"
        )

        raw = await self._call_llm(
            messages=[{"role": "user", "content": user_content}],
            system=system,
            session_id=session_id,
        )

        try:
            import json, re
            cleaned = raw.strip()
            # Strip markdown fences if any
            cleaned = re.sub(r"```\w*\n?", "", cleaned).strip()
            confirmed = json.loads(cleaned)
            if not isinstance(confirmed, list):
                confirmed = table_names
        except Exception:
            confirmed = table_names

        # Filter context to only confirmed tables
        confirmed_set = set(confirmed)
        filtered_tables = [
            t for t in tables
            if f"{t['table_schema']}.{t['table_name']}" in confirmed_set
        ] or tables  # fallback to all if filter empties the list

        # Rebuild context from filtered tables
        lines = ["# Relevant Database Schema\n"]
        for tbl in filtered_tables:
            lines.append(f"## {tbl['table_schema']}.{tbl['table_name']}")
            if tbl.get("description"):
                lines.append(f"Description: {tbl['description']}")
            lines.append("\nColumns:")
            for col in tbl.get("columns", []):
                markers = (" [PK]" if col.get("is_pk") else "") + (" [FK]" if col.get("is_fk") else "")
                desc = f" — {col['description']}" if col.get("description") else ""
                lines.append(f"  {col['column_name']} {col['data_type']}{markers}{desc}")
            lines.append("")

        return {
            "relevant_tables_context": "\n".join(lines),
            "tables_found": [f"{t['table_schema']}.{t['table_name']}" for t in filtered_tables],
        }
