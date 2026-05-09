import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import QueryExecutionNotFoundError
from app.core.redis_client import CacheClient, get_cache_client
from app.models.schemas.query import (
    AnalysisRequest,
    AnalysisResponse,
    QueryExecutionResponse,
)
from app.services.query_service import QueryService

router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    cache: CacheClient = Depends(get_cache_client),
) -> AnalysisResponse:
    """
    Main ARIA endpoint. Takes a natural-language question, runs the full
    Orchestrator pipeline (schema → SQL → execute → analysis), and returns
    a structured AnalysisResponse. Never raises raw exceptions.
    """
    svc = QueryService(db=db, cache=cache)
    return await svc.run_analysis(request)


@router.get("/{session_id}/history", response_model=List[QueryExecutionResponse])
async def get_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[QueryExecutionResponse]:
    """Returns all query executions for a session, newest first."""
    svc = QueryService(db=db)
    executions = await svc.list_executions(session_id)
    return [QueryExecutionResponse.model_validate(e) for e in executions]


@router.get("/execution/{execution_id}", response_model=QueryExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QueryExecutionResponse:
    """Returns a single query execution with full result_preview."""
    svc = QueryService(db=db)
    execution = await svc.get_execution(execution_id)
    if not execution:
        raise QueryExecutionNotFoundError(str(execution_id))
    return QueryExecutionResponse.model_validate(execution)
