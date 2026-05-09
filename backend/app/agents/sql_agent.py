import json
import re
import uuid
from typing import Optional

import sqlglot
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.config import settings
from app.core.exceptions import LLMError
from app.utils.sql_validator import validate_sql

_SYSTEM_PROMPT = """You are a SQL expert for {dialect}.

Given a natural language question and the relevant database schema, generate ONE valid SQL SELECT query.

Rules:
- Only SELECT queries are allowed (no INSERT, UPDATE, DELETE, DROP, etc.)
- Use the exact table and column names from the schema provided
- Add a LIMIT if the query might return many rows (use LIMIT 10000 as default)
- Write clean, readable SQL with proper formatting

Respond with ONLY a valid JSON object — no markdown, no backticks, no explanation outside the JSON:
{{
  "sql": "SELECT ...",
  "explanation": "Plain-English explanation of what this query does and why",
  "tables_used": ["schema.table1", "schema.table2"],
  "estimated_rows": "~100 rows",
  "confidence": "high|medium|low"
}}"""


class SQLAgent(BaseAgent):
    """
    Translates natural language questions into validated SQL queries.
    Uses claude-sonnet-4-6 for careful reasoning. Retries on validation failure.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=None)
        self.model = self.model_smart

    async def run(self, input: dict, session_context: dict) -> dict:
        question: str = input["question"]
        schema_context: str = input.get("schema_context", "No schema available.")
        dialect: str = input.get("db_dialect", "postgres")
        business_context: str = input.get("business_context", "")
        session_history: str = input.get("session_history_summary", "")
        last_error: Optional[str] = input.get("last_error")

        session_id_raw = session_context.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None

        system = _SYSTEM_PROMPT.format(dialect=dialect)

        parts = [
            f"Question: {question}",
            f"\nDatabase Schema:\n{schema_context}",
        ]
        if business_context:
            parts.append(f"\nBusiness Context:\n{business_context}")
        if session_history:
            parts.append(f"\nPrevious Analysis Summary:\n{session_history}")
        if last_error:
            parts.append(
                f"\n⚠️ A previous SQL attempt failed when executed:\n{last_error}\n"
                "Generate a corrected query that avoids this error."
            )

        messages = [{"role": "user", "content": "\n".join(parts)}]

        last_parse_error: Optional[str] = None

        for attempt in range(settings.sql_agent_max_retries):
            raw = await self._call_llm(
                messages=messages,
                system=system,
                session_id=session_id,
            )

            # Strip markdown fences if the model wraps output
            cleaned = raw.strip()
            cleaned = re.sub(r"```(?:json)?\s*", "", cleaned).strip().rstrip("`")

            # Parse JSON
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                last_parse_error = str(exc)
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your response was not valid JSON (error: {exc}). "
                        "Respond with ONLY a JSON object matching the required format."
                    ),
                })
                continue

            sql: str = (parsed.get("sql") or "").strip()
            if not sql:
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": "The 'sql' field was empty. Provide a complete SQL SELECT query.",
                })
                continue

            # Validate — must be read-only
            is_valid, validation_error = validate_sql(sql, read_only=True, dialect=dialect)
            if not is_valid:
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        f"The SQL failed validation: {validation_error}. "
                        "Fix the query and respond with corrected JSON."
                    ),
                })
                continue

            # Optionally transpile to target dialect for correctness
            try:
                transpiled = sqlglot.transpile(sql, read="postgres", write=dialect)
                if transpiled:
                    sql = transpiled[0]
            except Exception:
                pass  # Use original SQL if transpilation fails

            return {
                "sql": sql,
                "explanation": parsed.get("explanation", ""),
                "tables_used": parsed.get("tables_used", []),
                "estimated_rows": parsed.get("estimated_rows", "unknown"),
                "confidence": parsed.get("confidence", "medium"),
            }

        raise LLMError(
            "SQLAgent",
            f"Failed to generate valid SQL after {settings.sql_agent_max_retries} attempts. "
            f"Last error: {last_parse_error or 'validation failure'}",
        )
