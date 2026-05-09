"""
Seed a DataConnection pointing at ARIA's own PostgreSQL instance, then
immediately trigger schema indexing so the Schema Brain knows all ARIA tables.

Usage (from repo root):
    docker-compose exec backend python scripts/seed_test_connection.py
"""
import asyncio
import json
import sys
import os

# Ensure the backend package root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db.models import DataConnection
from app.utils.encryption import encrypt


_CONNECTION_NAME = "ARIA Internal DB"
_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "database": "aria_db",
}
_CREDENTIALS = {
    "username": "aria",
    "password": "aria_secret",
}


async def main() -> None:
    async with AsyncSessionLocal() as db:
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
    print(f"  docker-compose exec backend python scripts/test_analysis.py {connection_id}")


if __name__ == "__main__":
    asyncio.run(main())
