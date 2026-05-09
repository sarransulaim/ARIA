import time
from typing import Any, Dict, List, Optional

import asyncpg

from app.connectors.base import BaseConnector
from app.core.exceptions import QueryExecutionError


class PostgreSQLConnector(BaseConnector):
    def get_dialect(self) -> str:
        return "postgres"

    def _dsn(self) -> str:
        host = self.config.get("host", "localhost")
        port = int(self.config.get("port", 5432))
        database = self.config.get("database", "")
        user = self.credentials.get("username", "")
        password = self.credentials.get("password", "")
        ssl = self.config.get("ssl", False)
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        if ssl:
            dsn += "?sslmode=require"
        return dsn

    async def _connect(self) -> asyncpg.Connection:
        return await asyncpg.connect(self._dsn(), timeout=10)

    async def test_connection(self) -> dict:
        start = time.monotonic()
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await self._connect()
            await conn.fetchval("SELECT 1")
            latency_ms = int((time.monotonic() - start) * 1000)
            return {"success": True, "latency_ms": latency_ms, "error": None}
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return {"success": False, "latency_ms": latency_ms, "error": str(exc)}
        finally:
            if conn and not conn.is_closed():
                await conn.close()

    async def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> dict:
        start = time.monotonic()
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await self._connect()
            # asyncpg uses positional $1,$2 params; pass as list if provided
            args: List[Any] = list(params.values()) if params else []
            records = await conn.fetch(sql, *args)
            execution_time_ms = int((time.monotonic() - start) * 1000)
            if records:
                columns = list(records[0].keys())
                rows = [list(r.values()) for r in records]
            else:
                columns = []
                rows = []
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": execution_time_ms,
            }
        except Exception as exc:
            raise QueryExecutionError(str(exc))
        finally:
            if conn and not conn.is_closed():
                await conn.close()

    async def get_raw_schema(self) -> dict:
        conn: Optional[asyncpg.Connection] = None
        try:
            conn = await self._connect()

            tables = await conn.fetch(
                """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )

            schema: Dict[str, Any] = {}
            for tbl in tables:
                table_schema = tbl["table_schema"]
                table_name = tbl["table_name"]

                columns = await conn.fetch(
                    """
                    SELECT
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.numeric_scale,
                        CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_pk,
                        CASE WHEN fk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_fk
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                          ON tc.constraint_name = ku.constraint_name
                         AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_schema = $1 AND tc.table_name = $2
                    ) pk ON c.column_name = pk.column_name
                    LEFT JOIN (
                        SELECT ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                          ON tc.constraint_name = ku.constraint_name
                         AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_schema = $1 AND tc.table_name = $2
                    ) fk ON c.column_name = fk.column_name
                    WHERE c.table_schema = $1 AND c.table_name = $2
                    ORDER BY c.ordinal_position
                    """,
                    table_schema,
                    table_name,
                )

                key = f"{table_schema}.{table_name}"
                schema[key] = {
                    "schema": table_schema,
                    "table": table_name,
                    "table_type": tbl["table_type"],
                    "columns": [dict(col) for col in columns],
                }

            return schema
        finally:
            if conn and not conn.is_closed():
                await conn.close()
