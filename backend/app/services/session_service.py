import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SessionNotFoundError
from app.models.db.models import Message, Session
from app.models.schemas.session import SessionCreate, SessionResponse, MessageResponse, SessionUpdate

_SENTINEL_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _to_message_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        message_type=msg.message_type,
        content=msg.content,
        metadata=msg.msg_metadata or {},
        parent_message_id=msg.parent_message_id,
        created_at=msg.created_at,
    )


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: SessionCreate) -> Session:
        user_id = payload.user_id or _SENTINEL_USER_ID
        session = Session(
            user_id=user_id,
            connection_id=payload.connection_id,
            title=payload.title or "New Analysis",
            status="active",
            key_findings=[],
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[Session]:
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _message_count(self, session_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Message.id)).where(Message.session_id == session_id)
        )
        return result.scalar_one() or 0

    async def to_response(self, session: Session) -> SessionResponse:
        count = await self._message_count(session.id)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            connection_id=session.connection_id,
            title=session.title,
            status=session.status,
            session_summary=session.session_summary,
            key_findings=session.key_findings or [],
            message_count=count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    async def list_by_user(
        self,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Session]:
        q = select(Session)
        if user_id:
            q = q.where(Session.user_id == user_id)
        q = q.order_by(Session.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update(self, session_id: uuid.UUID, payload: SessionUpdate) -> Session:
        session = await self.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(str(session_id))
        if payload.title is not None:
            session.title = payload.title
        if payload.status is not None:
            session.status = payload.status
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_message_id: Optional[uuid.UUID] = None,
    ) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            message_type=message_type,
            content=content,
            msg_metadata=metadata or {},
            parent_message_id=parent_message_id,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def get_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MessageResponse]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        msgs = result.scalars().all()
        return [_to_message_response(m) for m in msgs]

    async def update_summary(
        self,
        session_id: uuid.UUID,
        summary: str,
        findings: List[Any],
    ) -> None:
        session = await self.get_by_id(session_id)
        if not session:
            return
        session.session_summary = summary
        existing = session.key_findings or []
        for f in findings:
            if f and f not in existing:
                existing.append(f)
        session.key_findings = existing[-20:]  # keep last 20 findings
        await self.db.flush()

    async def archive(self, session_id: uuid.UUID) -> None:
        session = await self.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(str(session_id))
        session.status = "archived"
        await self.db.flush()
