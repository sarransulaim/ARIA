from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    session_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=5000)
    connection_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None


class AnalysisArtifact(BaseModel):
    artifact_type: str  # sql | table | chart | statistics | insights | query_plan | stat_card
    title: str
    data: Dict[str, Any]


class StepResult(BaseModel):
    step: int
    sql: str
    explanation: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: int


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
    # Rich fields added by the senior analyst upgrade
    analysis_type: Optional[str] = None
    analysis_title: Optional[str] = None
    artifacts: List[AnalysisArtifact] = []
    key_insights: List[str] = []
    statistical_summary: Optional[Dict[str, Any]] = None
    data_quality_warnings: List[str] = []
    query_plan: List[str] = []
    all_charts: List[Dict[str, Any]] = []
    all_step_results: List[StepResult] = []


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
