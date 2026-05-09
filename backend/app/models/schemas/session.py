from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    connection_id: uuid.UUID
    title: Optional[str] = Field(None, max_length=500)
    user_id: Optional[uuid.UUID] = None  # populated from auth header in Phase 7


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    connection_id: uuid.UUID
    title: str
    status: str
    session_summary: Optional[str] = None
    key_findings: List[Any] = []
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    message_type: str
    content: str
    metadata: Dict[str, Any] = {}
    parent_message_id: Optional[uuid.UUID] = None
    created_at: datetime
