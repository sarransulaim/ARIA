import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import OrchestratorAgent
from app.core.exceptions import QueryExecutionNotFoundError
from app.core.redis_client import CacheClient
from app.models.db.models import QueryExecution
from app.models.schemas.query import AnalysisRequest, AnalysisResponse


class QueryService:
    def __init__(self, db: AsyncSession, cache: Optional[CacheClient] = None):
        self.db = db
        self.cache = cache

    async def run_analysis(self, request: AnalysisRequest) -> AnalysisResponse:
        orchestrator = OrchestratorAgent(db=self.db, cache=self.cache)
        result = await orchestrator.run(
            input={
                "question": request.question,
                "session_id": str(request.session_id),
                "connection_id": str(request.connection_id),
                "user_id": str(request.user_id) if request.user_id else None,
            },
            session_context={},
        )
        return AnalysisResponse(**result)

    async def get_execution(self, query_execution_id: uuid.UUID) -> Optional[QueryExecution]:
        result = await self.db.execute(
            select(QueryExecution).where(QueryExecution.id == query_execution_id)
        )
        return result.scalar_one_or_none()

    async def list_executions(self, session_id: uuid.UUID) -> List[QueryExecution]:
        result = await self.db.execute(
            select(QueryExecution)
            .where(QueryExecution.session_id == session_id)
            .order_by(QueryExecution.created_at.desc())
        )
        return list(result.scalars().all())
