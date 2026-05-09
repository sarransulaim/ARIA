# ARIA — Claude Code Master Guide
> Read this entire file before writing a single line of code.
> Nothing has been built yet. You are starting from zero.
> Every decision here was made intentionally. Follow the patterns exactly.

---

## What ARIA Is

ARIA (Analytical Research & Intelligence Assistant) is an AI-powered data analyst agent.

**The problem it solves:**
Brilliant analytical thinkers get filtered out because they can't write SQL fast enough.
ARIA separates thinking (human) from execution (AI).

**Core philosophy:**
- The human is the analyst. They think, decide, and direct.
- ARIA executes. It writes SQL, runs queries, interprets results, builds reports.
- ARIA never acts autonomously. It surfaces findings and waits for the human's call.
- Every SQL query ARIA writes is shown to the human. Full transparency. Glass box, not black box.
- The human only ever talks to the Orchestrator agent. Never to specialist agents directly.

---

## Architecture

### The 8-Layer System

```
HUMAN LAYER          → The analyst. Plain language. Decisions. Direction.
INTERFACE LAYER      → Conversational UI + Analysis Canvas + Decision Log
ARIA BRAIN LAYER     → Orchestrator + 5 specialist agents
EXECUTION LAYER      → SQL Generator, Query Optimizer, Code Sandbox, Viz Engine, Stats Engine
KNOWLEDGE LAYER      → Schema Brain, Business Context Store, Metadata, Glossary
DATA CONNECTOR LAYER → Every DB type, files, APIs
OUTPUT LAYER         → Reports (Word/PDF), Decks (PPTX/Google Slides), Dashboards
INFRASTRUCTURE       → Auth (Clerk), Security, Job Queue (Celery), Session Storage
```

### The 6-Agent System

```
Human
  ↓
ORCHESTRATOR AGENT  ← only agent the human ever talks to
  ↓         ↓         ↓          ↓           ↓
SQL       ANALYST   SCHEMA    PROACTIVE   OUTPUT
AGENT     AGENT     AGENT     AGENT       AGENT
```

**Rules that cannot ever be broken:**
1. Human ONLY talks to the Orchestrator
2. Orchestrator NEVER executes anything itself — only directs
3. Specialist agents NEVER talk to each other — everything routes through Orchestrator
4. Every SQL query shown to the human with plain English explanation
5. ARIA surfaces insights, human decides what to do with them

### Agent Responsibilities

| Agent | Only Job | Gets In Context |
|---|---|---|
| Orchestrator | Route requests, manage flow, surface results | Everything |
| SQL Agent | NL → SQL, validated, optimized, explained | Filtered schema, DB dialect, query rules |
| Analyst Agent | Interpret results, write narrative, generate hypotheses | Query results, session history, business context |
| Schema Agent | Understand DB structure, find relevant tables/columns | Raw schema, metadata |
| Proactive Agent | Background scanning, surface unsolicited insights | Data patterns, session context |
| Output Agent | Transform session into report or deck | Full session narrative, all visualizations |

---

## Tech Stack

### Backend
- **Language:** Python 3.11
- **Framework:** FastAPI (async — we need async for streaming responses)
- **ORM:** SQLAlchemy 2.0 async (every DB call must be async)
- **Migrations:** Alembic
- **Task Queue:** Celery + Redis
- **SQL Processing:** SQLAlchemy + SQLGlot (SQLGlot handles dialect translation between DBs)
- **Data Processing:** Pandas + Polars (Polars for large datasets > 100k rows)
- **Stats Engine:** NumPy + SciPy (correlations, anomaly detection, regression)

### AI / LLM
- **Primary LLM:** Anthropic Claude via `anthropic` Python SDK
- **Fast model:** `claude-haiku-4-5-20251001` — intent parsing, quick classification
- **Smart model:** `claude-sonnet-4-6` — SQL generation, deep analysis, report writing
- **Orchestration:** LangChain + LangGraph
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dimensions) — for Schema Brain
- **Vector storage:** pgvector extension inside PostgreSQL (no separate vector DB)
- **Observability:** LangSmith (every prompt, chain, and response logged)

### Frontend
- **Framework:** Next.js 14 with App Router
- **Language:** TypeScript strict mode (no `any` types ever)
- **Styling:** Tailwind CSS + Shadcn/ui components
- **State:** Zustand (client state) + TanStack Query (server/async state)
- **Tables:** TanStack Table (virtualized for large query results)
- **Charts:** Recharts (standard charts) + D3.js (custom/complex charts)
- **SQL Editor:** Monaco Editor (same engine as VS Code)
- **Animations:** Framer Motion (streaming responses, panel transitions)

### Infrastructure
- **Primary DB:** PostgreSQL 16 with pgvector extension
- **Cache + Message Broker:** Redis 7
- **Auth:** Clerk (SSO, orgs, magic links)
- **Credential Storage:** Encrypted at rest in PostgreSQL (AES-256)
- **File Storage:** S3 / Cloudflare R2
- **Containers:** Docker + Docker Compose
- **CI/CD:** GitHub Actions

---

## Project Structure

Build this exact structure. Do not deviate.

```
aria/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── routes/
│   │   │           ├── __init__.py
│   │   │           ├── auth.py
│   │   │           ├── connections.py
│   │   │           ├── sessions.py
│   │   │           ├── queries.py
│   │   │           ├── analysis.py
│   │   │           ├── schema.py
│   │   │           └── outputs.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── orchestrator.py
│   │   │   ├── sql_agent.py
│   │   │   ├── analyst_agent.py
│   │   │   ├── schema_agent.py
│   │   │   ├── proactive_agent.py
│   │   │   └── output_agent.py
│   │   ├── connectors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── postgresql.py
│   │   │   ├── mysql.py
│   │   │   ├── snowflake.py
│   │   │   ├── bigquery.py
│   │   │   ├── csv_connector.py
│   │   │   └── registry.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── redis_client.py
│   │   │   └── exceptions.py
│   │   ├── knowledge/
│   │   │   ├── __init__.py
│   │   │   ├── schema_brain.py
│   │   │   └── context_store.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   └── models.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── connection.py
│   │   │       ├── session.py
│   │   │       ├── query.py
│   │   │       ├── message.py
│   │   │       └── output.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── connection_service.py
│   │   │   ├── session_service.py
│   │   │   ├── query_service.py
│   │   │   └── output_service.py
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── query_tasks.py
│   │   │   ├── schema_tasks.py
│   │   │   ├── output_tasks.py
│   │   │   └── proactive_tasks.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── encryption.py
│   │   │   ├── sql_validator.py
│   │   │   └── pagination.py
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   └── celery_app.py
│   │   └── main.py
│   ├── migrations/
│   │   └── init.sql
│   ├── tests/
│   │   └── __init__.py
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── chat/
│   │   │   ├── canvas/
│   │   │   ├── charts/
│   │   │   └── layout/
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   ├── store/
│   │   │   └── utils/
│   │   ├── types/
│   │   └── hooks/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
├── docker-compose.yml
├── .gitignore
└── CLAUDE.md
```

---

## Code Patterns — Follow These Exactly

### 1. FastAPI Route Pattern

```python
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import ConnectionNotFoundError
from app.models.schemas.connection import ConnectionCreate, ConnectionResponse
from app.services.connection_service import ConnectionService

router = APIRouter()

@router.post("/", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    payload: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
):
    service = ConnectionService(db)
    return await service.create(payload)

@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = ConnectionService(db)
    conn = await service.get_by_id(connection_id)
    if not conn:
        raise ConnectionNotFoundError(str(connection_id))
    return conn
```

### 2. Service Pattern

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class ConnectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, connection_id: uuid.UUID):
        result = await self.db.execute(
            select(DataConnection).where(DataConnection.id == connection_id)
        )
        return result.scalar_one_or_none()
```

### 3. Pydantic Schema Pattern

```python
from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict

class ConnectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    connector_type: ConnectorType
    description: Optional[str] = None

class ConnectionCreate(ConnectionBase):
    connection_config: dict
    credentials: dict

class ConnectionResponse(ConnectionBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

### 4. Connector Pattern

```python
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    def __init__(self, connection_config: dict, credentials: dict):
        self.config = connection_config
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> dict:
        """Returns {success: bool, latency_ms: int, error: str | None}"""

    @abstractmethod
    async def execute_query(self, sql: str, params: dict = None) -> dict:
        """Returns {columns: list, rows: list, row_count: int, execution_time_ms: int}"""

    @abstractmethod
    async def get_raw_schema(self) -> dict:
        """Returns full schema dict for Schema Brain"""

    @abstractmethod
    def get_dialect(self) -> str:
        """Returns SQLGlot dialect string: 'postgres', 'mysql', 'snowflake'"""
```

### 5. Agent Pattern

```python
from abc import ABC, abstractmethod
import anthropic
from app.core.config import settings

class BaseAgent(ABC):
    def __init__(self, model: str = None):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.anthropic_model_smart

    @abstractmethod
    async def run(self, input: dict, session_context: dict) -> dict:
        """Takes input + session context, returns structured output"""

    async def _call_llm(self, messages: list, system: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=settings.anthropic_max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text
```

### 6. DB Query Pattern — Always Async

```python
# CORRECT
from sqlalchemy import select
result = await db.execute(select(Model).where(Model.id == id))
item = result.scalar_one_or_none()

# WRONG — never
item = db.query(Model).filter(Model.id == id).first()
```

### 7. Config Pattern — Never os.environ

```python
# CORRECT
from app.core.config import settings
key = settings.anthropic_api_key

# WRONG
import os
key = os.environ.get("ANTHROPIC_API_KEY")
```

---

## Database Schema

### Base class for all models
Every table gets UUID primary key, `created_at`, `updated_at` from `ARIABase`.

### Tables
- `users` — Clerk mirror (clerk_id, email, name, is_active)
- `organizations` — team workspace (clerk_org_id, name, settings JSONB)
- `data_connections` — connected sources (name, connector_type, connection_config JSONB, credentials_encrypted, is_read_only, last_tested_at, schema_last_indexed_at)
- `schema_tables` — indexed tables (connection_id FK, table_schema, table_name, description, tags JSONB, embedding vector(1536))
- `schema_columns` — indexed columns (table_id FK, column_name, data_type, is_pk, is_fk, description, sample_values JSONB, embedding vector(1536))
- `business_context` — analyst-taught rules (connection_id FK, context_type, key, value)
- `sessions` — analysis workspace (user_id FK, connection_id FK, title, status, session_summary, key_findings JSONB)
- `messages` — all conversation (session_id FK, role, message_type, content, metadata JSONB, parent_message_id FK)
- `query_executions` — SQL audit trail (session_id FK, connection_id FK, sql_text, natural_language_prompt, status, execution_time_ms, row_count, result_preview JSONB, error_message)
- `visualizations` — charts (session_id FK, query_execution_id FK, chart_type, title, chart_config JSONB, is_pinned)
- `reports` — generated docs (session_id FK, title, report_format, status, storage_key)
- `presentations` — generated decks (session_id FK, title, pres_format, status, storage_key, google_slides_url)
- `agent_logs` — every LLM call (session_id FK, agent_type, model_used, input_tokens, output_tokens, latency_ms, success, error_message)

---

## Build Order

### Phase 1 — Foundation
1. `docker-compose.yml`
2. `backend/migrations/init.sql` — enable pgvector, uuid-ossp, pg_trgm
3. `backend/Dockerfile`
4. `backend/requirements.txt`
5. `backend/.env.example`
6. `backend/app/core/config.py` — Pydantic settings
7. `backend/app/core/database.py` — async engine, ARIABase, get_db()
8. `backend/app/core/redis_client.py` — cache, pub/sub, key builders
9. `backend/app/core/exceptions.py` — all custom exceptions
10. `backend/app/models/db/models.py` — all tables
11. `backend/app/workers/celery_app.py`
12. `backend/app/main.py` — FastAPI app, CORS, exception handlers, health check, all routers
13. All route stubs (empty routers so imports work)
14. All task stubs
15. `.gitignore`

**Test:** `GET /health` returns `{"status": "healthy"}`

### Phase 2 — Data Connectors
16. `backend/app/connectors/base.py`
17. `backend/app/connectors/postgresql.py`
18. `backend/app/connectors/registry.py`
19. `backend/app/utils/encryption.py`
20. `backend/app/utils/sql_validator.py`
21. `backend/app/models/schemas/connection.py`
22. `backend/app/services/connection_service.py`
23. `backend/app/api/v1/routes/connections.py`

**Test:** Create a connection, test it, get schema back

### Phase 3 — Schema Brain
24. `backend/app/knowledge/schema_brain.py`
25. `backend/app/tasks/schema_tasks.py`
26. `backend/app/api/v1/routes/schema.py`

**Test:** Connect a DB, index schema, search "find tables related to revenue"

### Phase 4 — Sessions
27. `backend/app/models/schemas/session.py` + `message.py`
28. `backend/app/services/session_service.py`
29. `backend/app/api/v1/routes/sessions.py`

### Phase 5 — Agents
30. `backend/app/agents/base.py`
31. `backend/app/agents/schema_agent.py`
32. `backend/app/agents/sql_agent.py`
33. `backend/app/agents/analyst_agent.py`
34. `backend/app/agents/orchestrator.py`
35. `backend/app/models/schemas/query.py`
36. `backend/app/services/query_service.py`
37. `backend/app/api/v1/routes/queries.py` — with SSE streaming

**Test:** Ask "show me total revenue by month" — get SQL + results + analysis back

### Phase 6 — Output Layer
38. `backend/app/agents/output_agent.py`
39. `backend/app/services/output_service.py`
40. `backend/app/tasks/output_tasks.py`
41. `backend/app/api/v1/routes/outputs.py`

### Phase 7 — Frontend
42. Next.js 14 setup (TypeScript + Tailwind + Shadcn)
43. Clerk auth
44. Connection management UI
45. Chat interface
46. Analysis canvas
47. Visualization components

### Phase 8 — Proactive Agent
48. `backend/app/agents/proactive_agent.py`
49. `backend/app/tasks/proactive_tasks.py`

---

## Naming Conventions

**Python:** `snake_case` files, `PascalCase` classes, `snake_case` functions/variables, `UPPER_SNAKE_CASE` constants, `_underscore` private methods, all handlers `async def`

**Database:** `snake_case` plural tables, `snake_case` columns, `{table_singular}_id` FKs, `ix_{table}_{col}` indexes, `uq_{table}_{cols}` unique constraints

**TypeScript:** `PascalCase.tsx` components, `useCamelCase.ts` hooks, `camelCase.ts` utils, `PascalCase` types, `use{Name}Store` Zustand stores

**API:** `kebab-case` paths, `snake_case` params and query strings

---

## 10 Rules That Cannot Be Broken

1. All backend DB calls are async — `await`, `AsyncSession`, `select()`
2. Never store credentials in plaintext — always encrypt before writing to DB
3. Never expose stack traces in API responses — global handler catches everything
4. Never use `os.environ` directly — always `from app.core.config import settings`
5. Never mutate data unless `is_read_only=False` AND user explicitly confirmed
6. Every new router must be registered in `main.py`
7. Every LLM call must be logged to `agent_logs` table
8. UUID primary keys everywhere — never integer IDs
9. Check feature flags before building optional features — `settings.feature_*`
10. Always show SQL to the human — SQL Agent must include the query in every response

---

## Requirements

### `backend/requirements.txt` — include these packages
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
pydantic==2.7.0
pydantic-settings==2.2.1
sqlalchemy==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
pgvector==0.2.5
redis[hiredis]==5.0.4
celery[redis]==5.3.6
anthropic==0.28.0
langchain==0.2.1
langchain-anthropic==0.1.11
langchain-community==0.2.1
langchain-openai==0.1.7
langgraph==0.1.1
openai==1.30.1
sqlglot==23.12.2
pandas==2.2.2
polars==0.20.22
numpy==1.26.4
scipy==1.13.0
httpx==0.27.0
cryptography==42.0.7
python-jose[cryptography]==3.3.0
python-dotenv==1.0.1
pymysql==1.1.1
python-docx==1.1.2
python-pptx==0.6.23
weasyprint==62.1
jinja2==3.1.4
plotly==5.22.0
kaleido==0.2.1
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-api-python-client==2.130.0
openpyxl==3.1.2
boto3==1.34.113
structlog==24.1.0
```

---

*Start with Phase 1. Complete and test each phase before moving to the next. The health endpoint must return healthy before anything else is built.*
