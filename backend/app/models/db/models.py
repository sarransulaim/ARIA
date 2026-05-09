import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False

from app.core.database import ARIABase


class User(ARIABase):
    __tablename__ = "users"

    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="user")


class Organization(ARIABase):
    __tablename__ = "organizations"

    clerk_org_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class DataConnection(ARIABase):
    __tablename__ = "data_connections"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    connection_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    schema_last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    schema_tables: Mapped[List["SchemaTable"]] = relationship(
        "SchemaTable", back_populates="connection", cascade="all, delete-orphan"
    )
    business_contexts: Mapped[List["BusinessContext"]] = relationship(
        "BusinessContext", back_populates="connection", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="connection")
    query_executions: Mapped[List["QueryExecution"]] = relationship(
        "QueryExecution", back_populates="connection"
    )


class SchemaTable(ARIABase):
    __tablename__ = "schema_tables"
    __table_args__ = (
        UniqueConstraint("connection_id", "table_schema", "table_name", name="uq_schema_tables_connection_schema_name"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_schema: Mapped[str] = mapped_column(String(255), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    embedding: Mapped[Optional[object]] = mapped_column(Vector(1536) if _VECTOR_AVAILABLE else Text, nullable=True)

    connection: Mapped["DataConnection"] = relationship("DataConnection", back_populates="schema_tables")
    columns: Mapped[List["SchemaColumn"]] = relationship(
        "SchemaColumn", back_populates="table", cascade="all, delete-orphan"
    )


class SchemaColumn(ARIABase):
    __tablename__ = "schema_columns"
    __table_args__ = (
        UniqueConstraint("table_id", "column_name", name="uq_schema_columns_table_col"),
    )

    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schema_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_pk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    sample_values: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    embedding: Mapped[Optional[object]] = mapped_column(Vector(1536) if _VECTOR_AVAILABLE else Text, nullable=True)

    table: Mapped["SchemaTable"] = relationship("SchemaTable", back_populates="columns")


class BusinessContext(ARIABase):
    __tablename__ = "business_context"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    context_type: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    connection: Mapped["DataConnection"] = relationship("DataConnection", back_populates="business_contexts")


class Session(ARIABase):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), default="New Analysis", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    session_summary: Mapped[Optional[str]] = mapped_column(Text)
    key_findings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    connection: Mapped["DataConnection"] = relationship("DataConnection", back_populates="sessions")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    query_executions: Mapped[List["QueryExecution"]] = relationship(
        "QueryExecution", back_populates="session", cascade="all, delete-orphan"
    )
    visualizations: Mapped[List["Visualization"]] = relationship(
        "Visualization", back_populates="session", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="session", cascade="all, delete-orphan"
    )
    presentations: Mapped[List["Presentation"]] = relationship(
        "Presentation", back_populates="session", cascade="all, delete-orphan"
    )
    agent_logs: Mapped[List["AgentLog"]] = relationship("AgentLog", back_populates="session")


class Message(ARIABase):
    __tablename__ = "messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    message_type: Mapped[str] = mapped_column(String(100), default="text", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    parent_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    parent: Mapped[Optional["Message"]] = relationship("Message", remote_side="Message.id")


class QueryExecution(ARIABase):
    __tablename__ = "query_executions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    natural_language_prompt: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    result_preview: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    session: Mapped["Session"] = relationship("Session", back_populates="query_executions")
    connection: Mapped["DataConnection"] = relationship("DataConnection", back_populates="query_executions")
    visualizations: Mapped[List["Visualization"]] = relationship("Visualization", back_populates="query_execution")


class Visualization(ARIABase):
    __tablename__ = "visualizations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("query_executions.id", ondelete="SET NULL"), nullable=True
    )
    chart_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    chart_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped["Session"] = relationship("Session", back_populates="visualizations")
    query_execution: Mapped[Optional["QueryExecution"]] = relationship(
        "QueryExecution", back_populates="visualizations"
    )


class Report(ARIABase):
    __tablename__ = "reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_format: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(1000))

    session: Mapped["Session"] = relationship("Session", back_populates="reports")


class Presentation(ARIABase):
    __tablename__ = "presentations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    pres_format: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(1000))
    google_slides_url: Mapped[Optional[str]] = mapped_column(String(2000))

    session: Mapped["Session"] = relationship("Session", back_populates="presentations")


class AgentLog(ARIABase):
    __tablename__ = "agent_logs"

    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_used: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    session: Mapped[Optional["Session"]] = relationship("Session", back_populates="agent_logs")
