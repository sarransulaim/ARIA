import asyncio
import json
import uuid

from sqlalchemy import select

from app.connectors.registry import get_connector
from app.core.database import AsyncSessionLocal
from app.knowledge.schema_brain import SchemaBrain
from app.models.db.models import AgentLog, DataConnection
from app.utils.encryption import decrypt
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.index_connection_schema", bind=True, max_retries=2)
def index_connection_schema(self, connection_id: str) -> dict:
    """
    Celery task: index the schema for a given connection_id.
    Triggered automatically after a connection is successfully tested.
    """
    return asyncio.run(_async_index(connection_id))


async def _async_index(connection_id: str) -> dict:
    from app.core.redis_client import get_cache_client

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(DataConnection).where(
                    DataConnection.id == uuid.UUID(connection_id)
                )
            )
            data_conn = result.scalar_one_or_none()
            if not data_conn:
                return {"success": False, "error": f"Connection {connection_id} not found"}

            credentials = json.loads(decrypt(data_conn.credentials_encrypted))
            connector = get_connector(
                data_conn.connector_type,
                data_conn.connection_config,
                credentials,
            )

            cache = await get_cache_client()

            brain = SchemaBrain(
                connection_id=uuid.UUID(connection_id),
                db=db,
                connector=connector,
                cache=cache,
            )
            await brain.index_schema()
            await db.commit()

            return {"success": True, "connection_id": connection_id}

        except Exception as exc:
            await db.rollback()
            try:
                error_log = AgentLog(
                    agent_type="schema_brain",
                    model_used="celery/index_connection_schema",
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=0,
                    success=False,
                    error_message=str(exc),
                )
                db.add(error_log)
                await db.commit()
            except Exception:
                pass
            return {"success": False, "error": str(exc)}
