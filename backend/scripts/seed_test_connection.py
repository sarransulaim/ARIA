"""
Seed a DataConnection pointing at ARIA's own PostgreSQL instance, then
immediately trigger schema indexing so the Schema Brain knows all ARIA tables.

Usage:
    # In Docker:
    docker-compose exec backend python scripts/seed_test_connection.py

    # Locally (from backend/):
    python scripts/seed_test_connection.py

The script derives the DB host, user, and password from DATABASE_URL in the
environment so it works identically inside Docker or a local venv.
"""
import asyncio
import json
import re
import sys
import os
import uuid

# Ensure the backend package root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.db.models import DataConnection, User
from app.utils.encryption import encrypt

# Matches _SENTINEL_USER_ID in session_service.py
_SENTINEL_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


_CONNECTION_NAME = "ARIA Internal DB"


def _parse_db_url(url: str) -> tuple[str, int, str, str, str]:
    """Return (host, port, database, user, password) from a SQLAlchemy DSN."""
    # Strip driver prefix: postgresql+asyncpg:// → postgresql://
    url = re.sub(r"^[^:]+\+[^:]+://", "postgresql://", url)
    m = re.match(
        r"postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<db>[^?]+)",
        url,
    )
    if not m:
        raise ValueError(f"Cannot parse DATABASE_URL: {url!r}")
    return (
        m.group("host"),
        int(m.group("port") or 5432),
        m.group("db"),
        m.group("user"),
        m.group("password"),
    )


_HOST, _PORT, _DATABASE, _USER, _PASSWORD = _parse_db_url(settings.database_url)

_CONFIG = {"host": _HOST, "port": _PORT, "database": _DATABASE}
_CREDENTIALS = {"username": _USER, "password": _PASSWORD}


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Ensure sentinel user exists (required by sessions FK).
        sentinel = await db.execute(
            select(User).where(User.id == _SENTINEL_USER_ID)
        )
        if not sentinel.scalar_one_or_none():
            db.add(User(
                id=_SENTINEL_USER_ID,
                clerk_id="seed-script",
                email="seed@aria.internal",
                name="Seed User",
                is_active=True,
            ))
            await db.flush()
            await db.commit()
            print("Created sentinel user for FK constraint.")

        # Upsert: if a connection with this name already exists, reuse it.
        existing = await db.execute(
            select(DataConnection).where(DataConnection.name == _CONNECTION_NAME)
        )
        conn = existing.scalar_one_or_none()

        if conn:
            print(f"Connection already exists — reusing: {conn.id}")
        else:
            credentials_encrypted = encrypt(json.dumps(_CREDENTIALS))
            conn = DataConnection(
                name=_CONNECTION_NAME,
                connector_type="postgresql",
                description="ARIA's own internal Postgres — used for end-to-end testing.",
                connection_config=_CONFIG,
                credentials_encrypted=credentials_encrypted,
                is_read_only=True,
                is_active=True,
            )
            db.add(conn)
            await db.flush()
            await db.refresh(conn)
            await db.commit()
            print(f"Created connection: {conn.id}")

        connection_id = str(conn.id)

    # Trigger schema indexing synchronously so the script blocks until complete.
    # We import the async helper directly to avoid needing a running Celery worker.
    print("Indexing schema — this may take a few seconds …")
    from app.tasks.schema_tasks import _async_index
    result = await _async_index(connection_id)

    if result.get("success"):
        print("Schema indexed successfully.")
    else:
        print(f"Schema indexing warning: {result.get('error')}", file=sys.stderr)

    print(f"\nconnection_id={connection_id}")
    print("\nNext step:")
    print(f"  python scripts/test_analysis.py {connection_id}")


if __name__ == "__main__":
    asyncio.run(main())
