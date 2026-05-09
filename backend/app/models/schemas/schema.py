from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ColumnDetail(BaseModel):
    id: uuid.UUID
    table_id: uuid.UUID
    column_name: str
    data_type: str
    is_pk: bool
    is_fk: bool
    is_nullable: bool
    description: Optional[str] = None
    sample_values: List[Any] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TableListItem(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    table_schema: str
    table_name: str
    description: Optional[str] = None
    tags: List[Any] = []
    column_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TableDetail(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    table_schema: str
    table_name: str
    description: Optional[str] = None
    tags: List[Any] = []
    created_at: datetime
    updated_at: datetime
    columns: List[ColumnDetail] = []

    model_config = ConfigDict(from_attributes=True)


class IndexJobResponse(BaseModel):
    job_id: str
    message: str


class SchemaStatusResponse(BaseModel):
    status: Literal["not_started", "running", "complete", "failed"]
    schema_last_indexed_at: Optional[datetime] = None
    table_count: int = 0
    job_id: Optional[str] = None


class SchemaSearchRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)


class TableSearchResult(BaseModel):
    table_schema: str
    table_name: str
    description: Optional[str] = None
    similarity: float
    columns: List[Dict[str, Any]] = []


class TableDescriptionUpdate(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)


class ColumnUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=2000)
    sample_values: Optional[List[Any]] = None
