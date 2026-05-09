from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ReportRequest(BaseModel):
    session_id: uuid.UUID
    format: Literal["pdf", "docx"] = "docx"
    audience: Optional[str] = Field(None, max_length=500)
    focus: Optional[str] = Field(None, max_length=500)


class PresentationRequest(BaseModel):
    session_id: uuid.UUID
    format: Literal["pptx"] = "pptx"
    audience: Optional[str] = Field(None, max_length=500)
    focus: Optional[str] = Field(None, max_length=500)


class OutputJobResponse(BaseModel):
    report_id: Optional[uuid.UUID] = None
    presentation_id: Optional[uuid.UUID] = None
    status: str


class ReportResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    report_format: str
    status: str
    storage_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresentationResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    pres_format: str
    status: str
    storage_key: Optional[str] = None
    google_slides_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionOutputsResponse(BaseModel):
    reports: List[ReportResponse]
    presentations: List[PresentationResponse]
