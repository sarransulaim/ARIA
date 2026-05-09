import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.models import BusinessContext


class ContextStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, connection_id: uuid.UUID, key: str) -> Optional[str]:
        result = await self.db.execute(
            select(BusinessContext).where(
                BusinessContext.connection_id == connection_id,
                BusinessContext.key == key,
            )
        )
        record = result.scalar_one_or_none()
        return record.value if record else None

    async def set(self, connection_id: uuid.UUID, context_type: str, key: str, value: str) -> BusinessContext:
        result = await self.db.execute(
            select(BusinessContext).where(
                BusinessContext.connection_id == connection_id,
                BusinessContext.key == key,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.value = value
        else:
            record = BusinessContext(
                connection_id=connection_id,
                context_type=context_type,
                key=key,
                value=value,
            )
            self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def list_for_connection(self, connection_id: uuid.UUID) -> List[BusinessContext]:
        result = await self.db.execute(
            select(BusinessContext).where(BusinessContext.connection_id == connection_id)
        )
        return list(result.scalars().all())

    async def delete(self, connection_id: uuid.UUID, key: str) -> bool:
        result = await self.db.execute(
            select(BusinessContext).where(
                BusinessContext.connection_id == connection_id,
                BusinessContext.key == key,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        await self.db.delete(record)
        await self.db.commit()
        return True
