from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ConnectorType(str, Enum):
    postgresql = "postgresql"
    mysql = "mysql"
    snowflake = "snowflake"
    bigquery = "bigquery"
    csv = "csv"


class ConnectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    connector_type: ConnectorType
    description: Optional[str] = None
    is_read_only: bool = True


class ConnectionCreate(ConnectionBase):
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, Any] = Field(...)


class ConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    is_read_only: Optional[bool] = None


class ConnectionResponse(ConnectionBase):
    id: uuid.UUID
    is_active: bool
    last_tested_at: Optional[datetime] = None
    schema_last_indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionTestResponse(BaseModel):
    success: bool
    latency_ms: int
    error: Optional[str] = None
