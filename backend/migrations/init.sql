-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table (mirrors Clerk)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_clerk_id ON users (clerk_id);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_org_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_organizations_clerk_org_id ON organizations (clerk_org_id);

-- Data connections table
CREATE TABLE IF NOT EXISTS data_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    connector_type VARCHAR(50) NOT NULL,
    description TEXT,
    connection_config JSONB NOT NULL DEFAULT '{}',
    credentials_encrypted TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_read_only BOOLEAN NOT NULL DEFAULT TRUE,
    last_tested_at TIMESTAMPTZ,
    schema_last_indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_data_connections_connector_type ON data_connections (connector_type);

-- Schema tables (indexed DB tables)
CREATE TABLE IF NOT EXISTS schema_tables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID NOT NULL REFERENCES data_connections(id) ON DELETE CASCADE,
    table_schema VARCHAR(255) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    description TEXT,
    tags JSONB NOT NULL DEFAULT '[]',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schema_tables_connection_schema_name UNIQUE (connection_id, table_schema, table_name)
);
CREATE INDEX IF NOT EXISTS ix_schema_tables_connection_id ON schema_tables (connection_id);
CREATE INDEX IF NOT EXISTS ix_schema_tables_embedding ON schema_tables USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Schema columns (indexed DB columns)
CREATE TABLE IF NOT EXISTS schema_columns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_id UUID NOT NULL REFERENCES schema_tables(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100) NOT NULL,
    is_pk BOOLEAN NOT NULL DEFAULT FALSE,
    is_fk BOOLEAN NOT NULL DEFAULT FALSE,
    is_nullable BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    sample_values JSONB NOT NULL DEFAULT '[]',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schema_columns_table_col UNIQUE (table_id, column_name)
);
CREATE INDEX IF NOT EXISTS ix_schema_columns_table_id ON schema_columns (table_id);
CREATE INDEX IF NOT EXISTS ix_schema_columns_embedding ON schema_columns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Business context (analyst-taught rules)
CREATE TABLE IF NOT EXISTS business_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID NOT NULL REFERENCES data_connections(id) ON DELETE CASCADE,
    context_type VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_business_context_connection_id ON business_context (connection_id);

-- Sessions (analysis workspaces)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES data_connections(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL DEFAULT 'New Analysis',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    session_summary TEXT,
    key_findings JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_connection_id ON sessions (connection_id);
CREATE INDEX IF NOT EXISTS ix_sessions_status ON sessions (status);

-- Messages (all conversation turns)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    message_type VARCHAR(100) NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    parent_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id);
CREATE INDEX IF NOT EXISTS ix_messages_parent_message_id ON messages (parent_message_id);

-- Query executions (SQL audit trail)
CREATE TABLE IF NOT EXISTS query_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES data_connections(id) ON DELETE CASCADE,
    sql_text TEXT NOT NULL,
    natural_language_prompt TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    execution_time_ms INTEGER,
    row_count INTEGER,
    result_preview JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_query_executions_session_id ON query_executions (session_id);
CREATE INDEX IF NOT EXISTS ix_query_executions_connection_id ON query_executions (connection_id);
CREATE INDEX IF NOT EXISTS ix_query_executions_status ON query_executions (status);

-- Visualizations (charts)
CREATE TABLE IF NOT EXISTS visualizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    query_execution_id UUID REFERENCES query_executions(id) ON DELETE SET NULL,
    chart_type VARCHAR(100) NOT NULL,
    title VARCHAR(500),
    chart_config JSONB NOT NULL DEFAULT '{}',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_visualizations_session_id ON visualizations (session_id);

-- Reports (generated documents)
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    report_format VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    storage_key VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_reports_session_id ON reports (session_id);

-- Presentations (generated decks)
CREATE TABLE IF NOT EXISTS presentations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    pres_format VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    storage_key VARCHAR(1000),
    google_slides_url VARCHAR(2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_presentations_session_id ON presentations (session_id);

-- Agent logs (every LLM call)
CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    agent_type VARCHAR(100) NOT NULL,
    model_used VARCHAR(255) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_logs_session_id ON agent_logs (session_id);
CREATE INDEX IF NOT EXISTS ix_agent_logs_agent_type ON agent_logs (agent_type);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'users','organizations','data_connections','schema_tables','schema_columns',
            'business_context','sessions','messages','query_executions',
            'visualizations','reports','presentations','agent_logs'
        ])
    LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_%s_updated_at ON %s;
             CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            t, t, t, t
        );
    END LOOP;
END;
$$;
