import uuid
from typing import List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConnectionNotFoundError, QueryExecutionNotFoundError
from app.core.redis_client import CacheClient, RedisKeys, get_cache_client
from app.knowledge.schema_brain import SchemaBrain
from app.models.db.models import DataConnection, SchemaColumn, SchemaTable
from app.models.schemas.schema import (
    ColumnDetail,
    ColumnUpdate,
    IndexJobResponse,
    SchemaSearchRequest,
    SchemaStatusResponse,
    TableDescriptionUpdate,
    TableDetail,
    TableListItem,
    TableSearchResult,
)
from app.tasks.schema_tasks import index_connection_schema
from app.workers.celery_app import celery_app

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _require_connection(connection_id: uuid.UUID, db: AsyncSession) -> DataConnection:
    result = await db.execute(
        select(DataConnection).where(DataConnection.id == connection_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise ConnectionNotFoundError(str(connection_id))
    return conn


def _celery_state_to_status(state: Optional[str]) -> str:
    if state in ("STARTED", "PENDING", "RETRY"):
        return "running"
    if state == "SUCCESS":
        return "complete"
    if state in ("FAILURE", "REVOKED"):
        return "failed"
    return "running"


# ── POST /{connection_id}/index ────────────────────────────────────────────────

@router.post("/{connection_id}/index", response_model=IndexJobResponse)
async def trigger_schema_index(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> IndexJobResponse:
    """Enqueue a Celery job that indexes (or re-indexes) this connection's schema."""
    await _require_connection(connection_id, db)

    task = index_connection_schema.delay(str(connection_id))

    # Persist task ID so the status endpoint can query it
    await cache.set(
        RedisKeys.schema_task(str(connection_id)),
        {"task_id": task.id},
        ttl_seconds=86400,
    )

    return IndexJobResponse(
        job_id=task.id,
        message="Schema indexing job queued.",
    )


# ── GET /{connection_id}/status ────────────────────────────────────────────────

@router.get("/{connection_id}/status", response_model=SchemaStatusResponse)
async def get_schema_status(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> SchemaStatusResponse:
    data_conn = await _require_connection(connection_id, db)

    table_count_result = await db.execute(
        select(func.count(SchemaTable.id)).where(
            SchemaTable.connection_id == connection_id
        )
    )
    table_count = table_count_result.scalar_one() or 0

    task_info = await cache.get(RedisKeys.schema_task(str(connection_id)))
    job_id: Optional[str] = None

    if task_info and isinstance(task_info, dict):
        job_id = task_info.get("task_id")
        celery_state = AsyncResult(job_id, app=celery_app).state
        status = _celery_state_to_status(celery_state)
    elif data_conn.schema_last_indexed_at:
        status = "complete"
    else:
        status = "not_started"

    return SchemaStatusResponse(
        status=status,
        schema_last_indexed_at=data_conn.schema_last_indexed_at,
        table_count=table_count,
        job_id=job_id,
    )


# ── GET /{connection_id}/tables ────────────────────────────────────────────────

@router.get("/{connection_id}/tables", response_model=List[TableListItem])
async def list_tables(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> List[TableListItem]:
    await _require_connection(connection_id, db)

    cache_key = RedisKeys.schema_cache(str(connection_id))
    cached = await cache.get(cache_key)
    if cached and isinstance(cached, list):
        return [TableListItem(**t) for t in cached]

    result = await db.execute(
        select(SchemaTable)
        .where(SchemaTable.connection_id == connection_id)
        .order_by(SchemaTable.table_schema, SchemaTable.table_name)
    )
    tables = result.scalars().all()

    items: List[TableListItem] = []
    for tbl in tables:
        col_count_result = await db.execute(
            select(func.count(SchemaColumn.id)).where(SchemaColumn.table_id == tbl.id)
        )
        col_count = col_count_result.scalar_one() or 0
        items.append(
            TableListItem(
                id=tbl.id,
                connection_id=tbl.connection_id,
                table_schema=tbl.table_schema,
                table_name=tbl.table_name,
                description=tbl.description,
                tags=tbl.tags or [],
                column_count=col_count,
                created_at=tbl.created_at,
                updated_at=tbl.updated_at,
            )
        )

    await cache.set(
        cache_key,
        [i.model_dump(mode="json") for i in items],
        ttl_seconds=settings.schema_cache_ttl,
    )
    return items


# ── GET /{connection_id}/tables/{table_name} ───────────────────────────────────

@router.get("/{connection_id}/tables/{table_name}", response_model=TableDetail)
async def get_table(
    connection_id: uuid.UUID,
    table_name: str,
    table_schema: str = Query("public"),
    db: AsyncSession = Depends(get_db),
) -> TableDetail:
    await _require_connection(connection_id, db)

    result = await db.execute(
        select(SchemaTable).where(
            SchemaTable.connection_id == connection_id,
            SchemaTable.table_schema == table_schema,
            SchemaTable.table_name == table_name,
        )
    )
    tbl = result.scalar_one_or_none()
    if tbl is None:
        raise QueryExecutionNotFoundError(f"{table_schema}.{table_name}")

    col_result = await db.execute(
        select(SchemaColumn)
        .where(SchemaColumn.table_id == tbl.id)
        .order_by(SchemaColumn.column_name)
    )
    columns = col_result.scalars().all()

    return TableDetail(
        id=tbl.id,
        connection_id=tbl.connection_id,
        table_schema=tbl.table_schema,
        table_name=tbl.table_name,
        description=tbl.description,
        tags=tbl.tags or [],
        created_at=tbl.created_at,
        updated_at=tbl.updated_at,
        columns=[ColumnDetail.model_validate(col) for col in columns],
    )


# ── POST /{connection_id}/search ───────────────────────────────────────────────

@router.post("/{connection_id}/search", response_model=List[TableSearchResult])
async def search_schema(
    connection_id: uuid.UUID,
    body: SchemaSearchRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> List[TableSearchResult]:
    await _require_connection(connection_id, db)

    brain = SchemaBrain(
        connection_id=connection_id,
        db=db,
        connector=None,
        cache=cache,
    )
    tables = await brain.find_relevant_tables(body.question, top_k=body.top_k)

    return [
        TableSearchResult(
            table_schema=t["table_schema"],
            table_name=t["table_name"],
            description=t.get("description"),
            similarity=t["similarity"],
            columns=t.get("columns", []),
        )
        for t in tables
    ]


# ── PATCH /{connection_id}/tables/{table_name} ─────────────────────────────────

@router.patch("/{connection_id}/tables/{table_name}", response_model=TableListItem)
async def update_table_description(
    connection_id: uuid.UUID,
    table_name: str,
    body: TableDescriptionUpdate,
    table_schema: str = Query("public"),
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> TableListItem:
    await _require_connection(connection_id, db)

    result = await db.execute(
        select(SchemaTable).where(
            SchemaTable.connection_id == connection_id,
            SchemaTable.table_schema == table_schema,
            SchemaTable.table_name == table_name,
        )
    )
    tbl = result.scalar_one_or_none()
    if tbl is None:
        raise QueryExecutionNotFoundError(f"{table_schema}.{table_name}")

    tbl.description = body.description
    await db.flush()

    # Invalidate cache so next list call reflects the new description
    await cache.delete(RedisKeys.schema_cache(str(connection_id)))

    col_count_result = await db.execute(
        select(func.count(SchemaColumn.id)).where(SchemaColumn.table_id == tbl.id)
    )
    col_count = col_count_result.scalar_one() or 0

    return TableListItem(
        id=tbl.id,
        connection_id=tbl.connection_id,
        table_schema=tbl.table_schema,
        table_name=tbl.table_name,
        description=tbl.description,
        tags=tbl.tags or [],
        column_count=col_count,
        created_at=tbl.created_at,
        updated_at=tbl.updated_at,
    )


# ── PATCH /{connection_id}/columns/{column_id} ─────────────────────────────────

@router.patch("/{connection_id}/columns/{column_id}", response_model=ColumnDetail)
async def update_column(
    connection_id: uuid.UUID,
    column_id: uuid.UUID,
    body: ColumnUpdate,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> ColumnDetail:
    await _require_connection(connection_id, db)

    result = await db.execute(
        select(SchemaColumn)
        .join(SchemaTable, SchemaColumn.table_id == SchemaTable.id)
        .where(
            SchemaColumn.id == column_id,
            SchemaTable.connection_id == connection_id,
        )
    )
    col = result.scalar_one_or_none()
    if col is None:
        raise QueryExecutionNotFoundError(str(column_id))

    if body.description is not None:
        col.description = body.description
    if body.sample_values is not None:
        col.sample_values = body.sample_values

    await db.flush()

    # Invalidate schema list cache
    await cache.delete(RedisKeys.schema_cache(str(connection_id)))

    return ColumnDetail.model_validate(col)
