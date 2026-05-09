"""
End-to-end analysis test using ARIA's own PostgreSQL database.

Creates a session against the seeded connection, sends a hard analytical
question to the full Orchestrator pipeline, and prints the complete response.

Usage:
    docker-compose exec backend python scripts/test_analysis.py <connection_id>

Run seed_test_connection.py first to obtain the connection_id.
"""
import asyncio
import json
import sys
import os
import textwrap
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


_QUESTION = (
    "Which agent type has the highest average latency and how many calls has it made?"
)


async def main(connection_id_str: str) -> None:
    try:
        connection_id = uuid.UUID(connection_id_str)
    except ValueError:
        print(f"Error: '{connection_id_str}' is not a valid UUID.", file=sys.stderr)
        sys.exit(1)

    from app.core.database import AsyncSessionLocal
    from app.core.redis_client import get_cache_client
    from app.models.schemas.session import SessionCreate
    from app.models.schemas.query import AnalysisRequest
    from app.services.session_service import SessionService
    from app.services.query_service import QueryService

    async with AsyncSessionLocal() as db:
        # ── 1. Create session ────────────────────────────────────────────────
        session_svc = SessionService(db)
        session = await session_svc.create(
            SessionCreate(
                connection_id=connection_id,
                title="E2E Test — Agent Latency Analysis",
            )
        )
        await db.commit()
        print(f"Session created: {session.id}\n")

        # ── 2. Run analysis ──────────────────────────────────────────────────
        print(f"Question: {_QUESTION}\n")
        print("Running ARIA pipeline …\n")

        cache = await get_cache_client()
        query_svc = QueryService(db=db, cache=cache)

        response = await query_svc.run_analysis(
            AnalysisRequest(
                session_id=session.id,
                connection_id=connection_id,
                question=_QUESTION,
            )
        )

    # ── 3. Print results ─────────────────────────────────────────────────────
    _hr = "─" * 72

    print(_hr)
    print("SQL GENERATED")
    print(_hr)
    if response.sql_generated:
        print(response.sql_generated)
    else:
        print("(none)")

    if response.sql_explanation:
        print(f"\nExplanation: {response.sql_explanation}")

    print(f"\n{_hr}")
    print("QUERY RESULTS")
    print(_hr)
    if response.results_preview:
        columns = response.results_preview.get("columns", [])
        rows = response.results_preview.get("rows", [])
        if columns:
            col_widths = [
                max(len(str(c)), max((len(str(r[i])) for r in rows), default=0))
                for i, c in enumerate(columns)
            ]
            header = "  ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(columns))
            print(header)
            print("  ".join("-" * w for w in col_widths))
            for row in rows:
                print("  ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row)))
        print(f"\nRow count: {response.row_count}")
    else:
        print("(no results)")

    print(f"\n{_hr}")
    print("ANALYSIS NARRATIVE")
    print(_hr)
    print(textwrap.fill(response.analysis_narrative, width=72))

    if response.suggested_followups:
        print(f"\n{_hr}")
        print("SUGGESTED FOLLOW-UPS")
        print(_hr)
        for i, q in enumerate(response.suggested_followups, 1):
            print(f"  {i}. {q}")

    if response.error:
        print(f"\n[WARNING] Pipeline reported an error condition.", file=sys.stderr)

    print(f"\n{_hr}")
    print(f"session_id={session.id}")
    print(f"connection_id={connection_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/test_analysis.py <connection_id>",
            file=sys.stderr,
        )
        print(
            "       Run seed_test_connection.py first to get the connection_id.",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
