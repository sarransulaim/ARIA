import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import get_connector
from app.core.exceptions import ConnectionNotFoundError, EncryptionError
from app.models.db.models import DataConnection
from app.models.schemas.connection import (
    ConnectionCreate,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from app.utils.encryption import decrypt, encrypt


class ConnectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: ConnectionCreate) -> DataConnection:
        encrypted = encrypt(json.dumps(payload.credentials))
        conn = DataConnection(
            name=payload.name,
            connector_type=payload.connector_type.value,
            description=payload.description,
            connection_config=payload.connection_config,
            credentials_encrypted=encrypted,
            is_read_only=payload.is_read_only,
        )
        self.db.add(conn)
        await self.db.flush()
        await self.db.refresh(conn)
        return conn

    async def get_by_id(self, connection_id: uuid.UUID) -> Optional[DataConnection]:
        result = await self.db.execute(
            select(DataConnection).where(DataConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, include_inactive: bool = False) -> List[DataConnection]:
        q = select(DataConnection)
        if not include_inactive:
            q = q.where(DataConnection.is_active == True)  # noqa: E712
        q = q.order_by(DataConnection.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(self, connection_id: uuid.UUID, payload: ConnectionUpdate) -> DataConnection:
        conn = await self.get_by_id(connection_id)
        if not conn:
            raise ConnectionNotFoundError(str(connection_id))

        if payload.name is not None:
            conn.name = payload.name
        if payload.description is not None:
            conn.description = payload.description
        if payload.connection_config is not None:
            conn.connection_config = payload.connection_config
        if payload.credentials is not None:
            conn.credentials_encrypted = encrypt(json.dumps(payload.credentials))
        if payload.is_read_only is not None:
            conn.is_read_only = payload.is_read_only

        await self.db.flush()
        await self.db.refresh(conn)
        return conn

    async def soft_delete(self, connection_id: uuid.UUID) -> None:
        conn = await self.get_by_id(connection_id)
        if not conn:
            raise ConnectionNotFoundError(str(connection_id))
        conn.is_active = False
        await self.db.flush()

    async def test_connection(self, connection_id: uuid.UUID) -> ConnectionTestResponse:
        conn = await self.get_by_id(connection_id)
        if not conn:
            raise ConnectionNotFoundError(str(connection_id))

        try:
            credentials = json.loads(decrypt(conn.credentials_encrypted))
        except (EncryptionError, json.JSONDecodeError) as exc:
            return ConnectionTestResponse(
                success=False, latency_ms=0, error=f"Could not read credentials: {exc}"
            )

        try:
            connector = get_connector(conn.connector_type, conn.connection_config, credentials)
            result = await connector.test_connection()
        except Exception as exc:
            return ConnectionTestResponse(success=False, latency_ms=0, error=str(exc))

        if result.get("success"):
            conn.last_tested_at = datetime.now(timezone.utc)
            await self.db.flush()

        return ConnectionTestResponse(**result)
