from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    session_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=5000)
    connection_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None  # populated from auth header in Phase 7


class AnalysisResponse(BaseModel):
    message_id: Optional[str] = None
    sql_generated: Optional[str] = None
    sql_explanation: Optional[str] = None
    results_preview: Optional[Dict[str, Any]] = None
    row_count: int = 0
    analysis_narrative: str
    suggested_followups: List[str] = []
    visualization_config: Optional[Dict[str, Any]] = None
    error: bool = False


class QueryExecutionResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    connection_id: uuid.UUID
    sql_text: str
    natural_language_prompt: Optional[str] = None
    status: str
    execution_time_ms: Optional[int] = None
    row_count: Optional[int] = None
    result_preview: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
