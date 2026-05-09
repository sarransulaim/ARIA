import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConnectionNotFoundError
from app.models.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from app.services.connection_service import ConnectionService

router = APIRouter()


@router.post("/", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    payload: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    service = ConnectionService(db)
    return await service.create(payload)


@router.get("/", response_model=List[ConnectionResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db),
) -> List[ConnectionResponse]:
    service = ConnectionService(db)
    return await service.list_all()


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    service = ConnectionService(db)
    conn = await service.get_by_id(connection_id)
    if not conn:
        raise ConnectionNotFoundError(str(connection_id))
    return conn


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    service = ConnectionService(db)
    return await service.update(connection_id, payload)


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ConnectionService(db)
    await service.soft_delete(connection_id)


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectionTestResponse:
    service = ConnectionService(db)
    return await service.test_connection(connection_id)
