import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import SessionNotFoundError
from app.models.schemas.session import (
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
)
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    svc = SessionService(db)
    session = await svc.create(payload)
    return await svc.to_response(session)


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[SessionResponse]:
    svc = SessionService(db)
    sessions = await svc.list_by_user(user_id=user_id, limit=limit, offset=offset)
    return [await svc.to_response(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    svc = SessionService(db)
    session = await svc.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))
    return await svc.to_response(session)


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[MessageResponse]:
    svc = SessionService(db)
    session = await svc.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))
    return await svc.get_messages(session_id, limit=limit, offset=offset)


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    svc = SessionService(db)
    session = await svc.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))
    session = await svc.update(session_id, payload)
    return await svc.to_response(session)


@router.put("/{session_id}/archive", response_model=SessionResponse)
async def archive_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    svc = SessionService(db)
    session = await svc.get_by_id(session_id)
    if not session:
        raise SessionNotFoundError(str(session_id))
    await svc.archive(session_id)
    session = await svc.get_by_id(session_id)
    return await svc.to_response(session)
