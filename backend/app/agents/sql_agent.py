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

_SYSTEM = """\
You are an expert data engineer producing production-quality analytical SQL for {dialect}.

Write SQL that a senior analyst would be proud of:
- Use CTEs (WITH clause) for any multi-step logic — they're easier to read and debug
- Use window functions for rankings, running totals, period-over-period:
    ROW_NUMBER(), RANK(), DENSE_RANK(), LAG(), LEAD(), SUM() OVER(), AVG() OVER()
- Use conditional aggregation: SUM(CASE WHEN status = 'x' THEN amount END)
- Use PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY col) for medians
- Add meaningful column aliases — never col1, col2
- ORDER results meaningfully (value DESC for rankings, date ASC for trends)
- Apply LIMIT 10000 unless the question asks for top-N (then use that N)
- Only SELECT queries — no INSERT, UPDATE, DELETE, DROP, TRUNCATE, or DDL

Respond with ONLY a valid JSON object — no markdown, no backticks:
{
  "sql": "SELECT ...",
  "explanation": "Plain English: what this query computes and why this approach was chosen",
  "tables_used": ["schema.table1"],
  "confidence": "high|medium|low"
}
"""

_STEP_PREFIX = """\
This is step {step} of {total} in a multi-step analysis.
Step purpose: {purpose}
SQL approach hint: {hint}

"""


class SQLAgent(BaseAgent):
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

        # Multi-step fields
        step_purpose: str = input.get("step_purpose", "")
        step_hint: str = input.get("step_hint", "")
        is_multi_step: bool = bool(input.get("is_multi_step", False))
        total_steps: int = int(input.get("total_steps", 1))
        current_step: int = int(input.get("current_step", 1))

        session_id_raw = session_context.get("session_id")
        session_id = uuid.UUID(session_id_raw) if session_id_raw else None

        system = _SYSTEM.format(dialect=dialect)

        parts = []
        if is_multi_step and step_purpose:
            parts.append(_STEP_PREFIX.format(
                step=current_step, total=total_steps,
                purpose=step_purpose, hint=step_hint or "Use best judgment",
            ))
        parts.append(f"Question: {question}")
        parts.append(f"\nDatabase Schema:\n{schema_context}")
        if business_context:
            parts.append(f"\nBusiness Context:\n{business_context}")
        if session_history:
            parts.append(f"\nPrevious Analysis Summary:\n{session_history}")
        if last_error:
            parts.append(
                f"\n⚠️ Previous SQL attempt failed at execution:\n{last_error}\n"
                "Produce a corrected query that avoids this error."
            )

        messages = [{"role": "user", "content": "\n".join(parts)}]
        last_parse_error: Optional[str] = None

        for attempt in range(settings.sql_agent_max_retries):
            raw = await self._call_llm(messages=messages, system=system, session_id=session_id)
            cleaned = re.sub(r"```(?:json)?\s*", "", raw.strip()).strip().rstrip("`")

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                last_parse_error = str(exc)
                messages += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": (
                        f"Invalid JSON (error: {exc}). "
                        "Respond with ONLY the JSON object."
                    )},
                ]
                continue

            sql: str = (parsed.get("sql") or "").strip()
            if not sql:
                messages += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "The 'sql' field was empty. Provide a complete SELECT query."},
                ]
                continue

            is_valid, validation_error = validate_sql(sql, read_only=True, dialect=dialect)
            if not is_valid:
                messages += [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": (
                        f"SQL failed validation: {validation_error}. "
                        "Fix the query and return corrected JSON."
                    )},
                ]
                continue

            try:
                transpiled = sqlglot.transpile(sql, read="postgres", write=dialect)
                if transpiled:
                    sql = transpiled[0]
            except Exception:
                pass

            return {
                "sql": sql,
                "explanation": parsed.get("explanation", ""),
                "tables_used": parsed.get("tables_used", []),
                "confidence": parsed.get("confidence", "medium"),
            }

        raise LLMError(
            "SQLAgent",
            f"Failed to generate valid SQL after {settings.sql_agent_max_retries} attempts. "
            f"Last error: {last_parse_error or 'validation failure'}",
        )
