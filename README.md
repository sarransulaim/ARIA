# ARIA — Analytical Research & Intelligence Assistant

> **AI-powered senior data analyst.** Ask questions in plain English. Get production-quality SQL, statistical analysis, smart visualizations, and executive-level narratives — instantly.

---

## What Problem ARIA Solves

Brilliant analytical thinkers get filtered out because they can't write SQL fast enough. Business stakeholders sit on valuable data they can't query. Senior analysts spend hours on mechanical SQL instead of strategic thinking.

**ARIA separates thinking (human) from execution (AI).**

- The human is the analyst — they think, decide, and direct
- ARIA executes — writes SQL, runs queries, interprets results, builds reports
- Every SQL query is shown to the human with a plain-English explanation
- Glass box, not black box

---

## What ARIA Can Do

### Natural Language → Production SQL
Ask any question and get back SQL that a senior engineer would write — with CTEs, window functions, percentile computations, conditional aggregation, and meaningful aliases.

```
"Which agent type has the highest average latency and how many calls has it made?"
"Show me month-over-month revenue growth with running totals"
"Find the top 10 customers by lifetime value with their order frequency"
"Compare conversion rates across cohorts from the last 6 months"
```

### Multi-Step Analysis Planning
Complex questions are automatically broken into 2–4 SQL steps, each with its own purpose and approach. The orchestrator plans before it executes.

```
Step 1: Aggregate base metrics by segment
Step 2: Compute period-over-period deltas using LAG()
Step 3: Rank segments by delta, annotate with percentiles
```

### Statistical Analysis Engine
Every result set is automatically analyzed:
- **Pearson correlation matrix** — identifies relationships between numeric columns
- **Linear trend detection** — slope, R², p-value via scipy
- **Group comparisons** — Welch t-test (2 groups) or one-way ANOVA (3+)
- **IQR outlier detection** — flags anomalies in every numeric column
- **Full column profiling** — min/max/mean/median/std/percentiles/top values

### Smart Visualization Recommendations
Rules-based chart selection — no guessing:

| Data shape | Chart type |
|---|---|
| Date column + numeric(s) | Line chart (sorted by date) |
| Date column + 1 numeric | Area chart (trend fill) |
| Category + 1 numeric | Bar chart (sorted by value) |
| Category + 1 numeric (>8 cats) | Horizontal bar chart |
| Category + multiple numerics | Grouped bar chart |
| 2 numerics only | Scatter plot |
| Any numeric column | Stat card (sum / mean / max) |

All charts are Recharts-compatible and rendered live in the analysis canvas.

### Executive-Level Narrative
The Analyst Agent writes findings like a Principal Data Scientist presenting to C-suite:
- Bottom-line-up-front — most important number in sentence one
- Exact figures — never "many" or "high", always "47% higher" or "3.2x the average"
- Statistical evidence — cites correlation r=0.82, p<0.05, R²=0.91 when available
- Anomaly flags — small samples, high null rates, outliers
- Hypotheses — explains *why* the pattern exists
- Recommended next steps — specific follow-up questions, not generic advice

### Real-Time Streaming
The entire pipeline streams over Server-Sent Events (SSE). The frontend updates live as each step completes:

```
progress → plan → sql → result → stats → visualizations → narrative → done
```

### Schema Brain (pgvector Semantic Search)
Every table and column in your connected database is indexed with Claude-generated descriptions and OpenAI embeddings. When you ask a question, ARIA uses cosine similarity search to find the most relevant tables — not keyword matching. Falls back gracefully when OpenAI key is not configured.

### Session Memory
Every analysis session has a running summary and key findings list. Each new question gets the full session context, so ARIA understands "compare that to last month" without re-explaining.

### Credential Security
Database credentials are encrypted with AES-256-GCM before storage. They are never logged, never exposed in API responses, and decrypted only in memory at query time.

---

## Architecture

### The 8-Layer System

```
┌─────────────────────────────────────────────────────────────┐
│  HUMAN LAYER         The analyst. Plain language. Decisions. │
├─────────────────────────────────────────────────────────────┤
│  INTERFACE LAYER     Chat UI + Analysis Canvas + Decision Log│
├─────────────────────────────────────────────────────────────┤
│  ARIA BRAIN LAYER    Orchestrator + 5 specialist agents      │
├─────────────────────────────────────────────────────────────┤
│  EXECUTION LAYER     SQL Gen + Stats Engine + Viz Engine     │
├─────────────────────────────────────────────────────────────┤
│  KNOWLEDGE LAYER     Schema Brain + Business Context Store   │
├─────────────────────────────────────────────────────────────┤
│  DATA CONNECTOR      PostgreSQL, MySQL, Snowflake, BigQuery  │
├─────────────────────────────────────────────────────────────┤
│  OUTPUT LAYER        Reports (Word/PDF) + Decks (PPTX)       │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE      Clerk Auth + Celery + Redis + pgvector  │
└─────────────────────────────────────────────────────────────┘
```

### The 6-Agent System

```
                        Human
                          │
                          ▼
               ┌──────────────────┐
               │  ORCHESTRATOR    │  ← only agent the human ever talks to
               │     AGENT        │
               └──────────────────┘
          ┌─────────┬──────┬───────┬────────┐
          ▼         ▼      ▼       ▼        ▼
       ┌─────┐  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
       │ SQL │  │ANALST│ │SCHEMA│ │PROAC.│ │OUTPUT│
       │AGENT│  │AGENT │ │AGENT │ │AGENT │ │AGENT │
       └─────┘  └──────┘ └──────┘ └──────┘ └──────┘
```

**Iron rules:**
1. Human ONLY talks to the Orchestrator
2. Orchestrator NEVER executes anything itself — only directs
3. Specialist agents NEVER talk to each other
4. Every SQL query shown to the human with plain-English explanation
5. ARIA surfaces insights; human decides what to do with them

### Agent Responsibilities

| Agent | Responsibility | Model |
|---|---|---|
| **Orchestrator** | Route requests, manage multi-step pipeline, stream events | Sonnet (smart) |
| **SQL Agent** | NL → production SQL with CTEs/window functions/percentiles | Sonnet (smart) |
| **Analyst Agent** | Interpret results, write executive narrative, generate hypotheses | Sonnet (smart) |
| **Schema Agent** | Find relevant tables via pgvector similarity search | Haiku (fast) |
| **Proactive Agent** | Background scanning, unsolicited insights (feature-flagged) | Haiku (fast) |
| **Output Agent** | Transform session into report or deck | Sonnet (smart) |

### Analysis Pipeline (per question)

```
Question
   │
   ├─1─ Load session + connection context
   ├─2─ Schema Agent: find relevant tables (pgvector cosine similarity)
   ├─3─ Load business context rules
   ├─4─ Orchestrator: parse intent + plan 1–4 SQL steps
   │       ↓
   ├─5─ For each step:
   │       └─ SQL Agent: generate SQL (with CTE/window/percentile prompt)
   │       └─ Execute on live database (read-only)
   │       └─ Persist QueryExecution audit record
   │
   ├─6─ Statistics Engine: correlation, trend, group comparison, profiling
   ├─7─ Viz Recommender: select optimal chart types
   ├─8─ Analyst Agent: write senior-level narrative
   ├─9─ Persist all messages, update session summary
   └─10─ Return structured AnalysisResponse with all artifacts
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI (fully async) |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic + raw SQL (init.sql) |
| Task Queue | Celery + Redis |
| SQL Processing | SQLAlchemy + SQLGlot (dialect translation) |
| Data Processing | Pandas + Polars (Polars for >100k rows) |
| Statistics | NumPy + SciPy |

### AI / LLM
| Component | Technology |
|---|---|
| Primary LLM | Anthropic Claude (via `anthropic` Python SDK) |
| Fast model | `claude-haiku-4-5-20251001` — intent, schema, classification |
| Smart model | `claude-sonnet-4-6` — SQL generation, analysis, reports |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dimensions) |
| Vector storage | pgvector inside PostgreSQL (no separate vector DB) |
| Observability | LangSmith (every prompt, chain, response logged) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 14 with App Router |
| Language | TypeScript strict mode |
| Styling | Tailwind CSS + Shadcn/ui |
| State | Zustand (client) + TanStack Query (server/async) |
| Tables | TanStack Table (virtualized) |
| Charts | Recharts |
| SQL Editor | Monaco Editor (VS Code engine) |
| Animations | Framer Motion |
| Streaming | Fetch API + ReadableStream (SSE consumer) |

### Infrastructure
| Component | Technology |
|---|---|
| Primary DB | PostgreSQL 16 + pgvector extension |
| Cache + Queue | Redis 7 |
| Auth | Clerk (SSO, orgs, magic links) |
| Credential Storage | AES-256-GCM encrypted at rest in PostgreSQL |
| File Storage | AWS S3 / Cloudflare R2 |
| Containers | Docker + Docker Compose |

---

## Database Schema

```
users                    Clerk mirror (clerk_id, email, name, is_active)
organizations            Team workspaces (clerk_org_id, name, settings JSONB)
data_connections         Connected sources (connector_type, connection_config JSONB,
                         credentials_encrypted, is_read_only, schema_last_indexed_at)
schema_tables            Indexed tables (connection_id FK, table_schema, table_name,
                         description, tags JSONB, embedding vector(1536))
schema_columns           Indexed columns (table_id FK, column_name, data_type,
                         is_pk, is_fk, description, sample_values JSONB,
                         embedding vector(1536))
business_context         Analyst-taught rules (connection_id FK, context_type, key, value)
sessions                 Analysis workspaces (user_id FK, connection_id FK, title,
                         status, session_summary, key_findings JSONB)
messages                 All conversation turns (session_id FK, role, message_type,
                         content, metadata JSONB, parent_message_id FK)
query_executions         Full SQL audit trail (session_id FK, connection_id FK,
                         sql_text, natural_language_prompt, status,
                         execution_time_ms, row_count, result_preview JSONB)
visualizations           Charts (session_id FK, query_execution_id FK, chart_type,
                         title, chart_config JSONB, is_pinned)
reports                  Generated documents (session_id FK, title, report_format,
                         status, storage_key)
presentations            Generated decks (session_id FK, title, pres_format, status,
                         storage_key, google_slides_url)
agent_logs               Every LLM call (session_id FK, agent_type, model_used,
                         input_tokens, output_tokens, latency_ms, success)
```

pgvector indexes on `schema_tables.embedding` and `schema_columns.embedding` use `ivfflat` with cosine ops for fast approximate nearest-neighbour search.

---

## API Reference

All endpoints are under `/api/v1/`.

### Analysis
| Method | Path | Description |
|---|---|---|
| `POST` | `/analysis/` | Run full pipeline, return `AnalysisResponse` |
| `POST` | `/analysis/stream` | SSE stream of the full pipeline |
| `GET` | `/analysis/{session_id}/history` | All query executions for a session |
| `GET` | `/analysis/execution/{id}` | Single execution with full result preview |

### SSE Stream Event Types
```jsonc
// progress
{ "type": "progress", "step": "planning", "message": "Planning analysis…", "pct": 15 }

// plan
{ "type": "plan", "intent": "comparison", "title": "Agent Latency Analysis",
  "steps": [{ "step": 1, "purpose": "…", "sql_hint": "…" }] }

// sql (one per step)
{ "type": "sql", "step": 1, "sql": "WITH …", "explanation": "…", "tables_used": ["…"] }

// result (one per step)
{ "type": "result", "step": 1, "columns": ["agent_type", "avg_latency_ms"],
  "rows": [["schema_brain", 412]], "row_count": 4, "execution_time_ms": 18 }

// stats
{ "type": "stats", "data": { "profile": {…}, "correlation": {…}, "trend": {…} } }

// visualizations
{ "type": "visualizations", "charts": [{ "type": "bar", "x_key": "…", "y_keys": […] }] }

// narrative
{ "type": "narrative", "narrative": "…", "key_insights": […], "anomalies": […] }

// done — full structured response
{ "type": "done", "response": { …AnalysisResponse… } }
```

### Connections
| Method | Path | Description |
|---|---|---|
| `POST` | `/connections/` | Create a new data connection |
| `GET` | `/connections/` | List all connections |
| `GET` | `/connections/{id}` | Get connection details |
| `POST` | `/connections/{id}/test` | Test connectivity (returns latency_ms) |
| `DELETE` | `/connections/{id}` | Delete a connection |

### Sessions
| Method | Path | Description |
|---|---|---|
| `POST` | `/sessions/` | Create a new analysis session |
| `GET` | `/sessions/` | List sessions |
| `GET` | `/sessions/{id}` | Get session with messages |
| `PUT` | `/sessions/{id}` | Update title/status |
| `PUT` | `/sessions/{id}/archive` | Archive a session |

### Schema
| Method | Path | Description |
|---|---|---|
| `POST` | `/schema/{connection_id}/index` | Trigger schema indexing (async via Celery) |
| `GET` | `/schema/{connection_id}/tables` | List all indexed tables |
| `POST` | `/schema/{connection_id}/search` | Semantic search for relevant tables |

### Outputs
| Method | Path | Description |
|---|---|---|
| `POST` | `/outputs/reports/` | Generate a Word/PDF report from session |
| `GET` | `/outputs/reports/{id}` | Get report status / download URL |
| `POST` | `/outputs/presentations/` | Generate a PPTX deck from session |

---

## Response Schema

```typescript
interface AnalysisResponse {
  // Core fields
  message_id: string | null
  sql_generated: string | null        // Primary SQL query
  sql_explanation: string | null      // Plain English explanation
  results_preview: { columns: string[], rows: unknown[][] } | null
  row_count: number
  analysis_narrative: string          // Executive summary
  suggested_followups: string[]       // 3 specific next questions
  visualization_config: object | null // Primary chart config
  error: boolean

  // Rich fields
  analysis_type: string | null        // trend_analysis | comparison | ranking | …
  analysis_title: string | null       // Short descriptive title
  artifacts: AnalysisArtifact[]       // Ordered list of all output pieces
  key_insights: string[]              // Specific findings with exact numbers
  statistical_summary: object | null  // Correlation, trend, group comparison
  data_quality_warnings: string[]     // Small sample, high nulls, outliers
  query_plan: string[]                // Step purposes in order
  all_charts: ChartConfig[]           // All recommended visualizations
  all_step_results: StepResult[]      // All SQL steps with their results
}

// Artifact types rendered in the analysis canvas
type ArtifactType =
  | "query_plan"   // Multi-step analysis plan with numbered steps
  | "sql"          // SQL query + plain-English explanation
  | "table"        // Query result set with row count + execution time
  | "chart"        // Recharts visualization (line/area/bar/scatter)
  | "stat_card"    // Single-number KPI card (sum/mean/max)
  | "statistics"   // Statistical analysis (correlation/trend/ANOVA)
  | "insights"     // Key findings with exact numbers + anomaly flags
```

---

## Project Structure

```
aria/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base.py              BaseAgent (LLM calls, logging)
│   │   │   ├── orchestrator.py      Multi-step pipeline + SSE streaming
│   │   │   ├── sql_agent.py         NL → production SQL
│   │   │   ├── analyst_agent.py     Senior analyst narrative
│   │   │   ├── schema_agent.py      pgvector table search
│   │   │   ├── proactive_agent.py   Background insight scanning
│   │   │   └── output_agent.py      Report + deck generation
│   │   ├── analysis/
│   │   │   ├── statistics.py        StatisticsEngine (correlation/trend/ANOVA)
│   │   │   └── viz_recommender.py   VizRecommender (rules-based chart selection)
│   │   ├── api/v1/routes/
│   │   │   ├── queries.py           POST /analysis/ and POST /analysis/stream
│   │   │   ├── connections.py       CRUD + test
│   │   │   ├── sessions.py          Session management
│   │   │   ├── schema.py            Index + search schema
│   │   │   └── outputs.py           Report/deck generation
│   │   ├── connectors/
│   │   │   ├── base.py              BaseConnector ABC
│   │   │   ├── postgresql.py        Full async PostgreSQL implementation
│   │   │   ├── mysql.py             Stub (ready to implement)
│   │   │   ├── snowflake.py         Stub (ready to implement)
│   │   │   ├── bigquery.py          Stub (ready to implement)
│   │   │   └── csv_connector.py     Stub (ready to implement)
│   │   ├── knowledge/
│   │   │   ├── schema_brain.py      pgvector indexing + similarity search
│   │   │   └── context_store.py     Business rules store
│   │   ├── models/
│   │   │   ├── db/models.py         All 13 SQLAlchemy ORM models
│   │   │   └── schemas/             Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── query_service.py     run_analysis() + stream_analysis()
│   │   │   ├── session_service.py   Session + message persistence
│   │   │   ├── connection_service.py
│   │   │   └── output_service.py
│   │   └── tasks/
│   │       ├── schema_tasks.py      Async schema indexing (Celery)
│   │       ├── query_tasks.py       Background query execution
│   │       ├── output_tasks.py      Async report generation
│   │       └── proactive_tasks.py   Scheduled insight scanning
│   ├── scripts/
│   │   ├── seed_test_connection.py  Seed ARIA's own DB as a test connection
│   │   └── test_analysis.py        End-to-end pipeline test
│   └── migrations/
│       └── init.sql                 Schema + pgvector + pg_trgm setup
│
└── frontend/
    └── src/
        ├── app/(dashboard)/         Next.js App Router pages
        ├── components/
        │   ├── canvas/
        │   │   ├── analysis-canvas.tsx   Live streaming progress + artifact grid
        │   │   ├── artifact-card.tsx     Renders all 7 artifact types
        │   │   ├── sql-display.tsx       Monaco SQL editor (collapsible)
        │   │   └── results-table.tsx     Virtualized data table
        │   ├── charts/
        │   │   └── chart-renderer.tsx    Recharts wrapper (7 chart types)
        │   ├── chat/                     Chat panel + message bubbles
        │   ├── connections/              Connection management UI
        │   └── ui/                       Shadcn components
        ├── hooks/
        │   └── use-analysis.ts           SSE stream consumer
        ├── lib/
        │   ├── api/queries.ts            streamAnalysis() + REST calls
        │   └── store/chat-store.ts       Zustand: messages + canvas + streaming
        └── types/index.ts               All TypeScript interfaces
```

---

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Anthropic API key (`claude-haiku-4-5-20251001` and `claude-sonnet-4-6`)
- OpenAI API key (optional — used only for pgvector embeddings; ARIA works without it)

### 1. Clone and configure

```bash
git clone <repo-url>
cd aria
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in:
```bash
ANTHROPIC_API_KEY=sk-ant-...          # Required
OPENAI_API_KEY=sk-...                 # Optional (schema embeddings)
ENCRYPTION_KEY=<32-byte-base64>       # Required (generate below)
SECRET_KEY=<random-string>            # Required
```

Generate a secure encryption key:
```bash
python3 -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
```

### 2. Start all services

```bash
docker-compose up --build
```

This starts:
- `aria_db` — PostgreSQL 16 with pgvector (port 5432)
- `aria_redis` — Redis 7 (port 6379)
- `aria_backend` — FastAPI with hot-reload (port 8000)
- `aria_worker` — Celery worker

### 3. Verify the backend is healthy

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

Interactive API docs: http://localhost:8000/docs

### 4. Seed a test connection and index the schema

```bash
docker-compose exec backend python scripts/seed_test_connection.py
# Created connection: <uuid>
# Indexing schema — this may take a few seconds…
# Schema indexed successfully.
# connection_id=<uuid>
```

### 5. Run an end-to-end analysis test

```bash
docker-compose exec backend python scripts/test_analysis.py <connection_id>
```

This asks *"Which agent type has the highest average latency and how many calls has it made?"* against ARIA's own database and prints the full pipeline output — SQL, results table, narrative, and follow-up suggestions.

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

---

## Running Locally (without Docker)

```bash
# Start Postgres and Redis separately, then:
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# In another terminal:
celery -A app.workers.celery_app worker --loglevel=info
```

---

## Feature Flags

Set in `backend/.env`:

| Flag | Default | Description |
|---|---|---|
| `FEATURE_PROACTIVE_AGENT` | `false` | Background insight scanning |
| `FEATURE_GOOGLE_SLIDES` | `false` | Export to Google Slides |
| `FEATURE_WEASYPRINT` | `false` | PDF export via WeasyPrint |

---

## Supported Data Sources

| Connector | Status | Notes |
|---|---|---|
| PostgreSQL | Full | Async, schema indexing, pgvector compatible |
| MySQL | Stub | Interface defined, driver ready |
| Snowflake | Stub | Interface defined |
| BigQuery | Stub | Interface defined |
| CSV / DuckDB | Stub | Interface defined |

All connectors implement the same `BaseConnector` interface: `test_connection()`, `execute_query()`, `get_raw_schema()`, `get_dialect()`.

---

## Security

- **Credentials encrypted at rest** — AES-256-GCM via `cryptography` library. Decrypted only in memory at query time, never logged or returned in API responses.
- **Read-only by default** — All connections default to `is_read_only=True`. SQL Agent only generates `SELECT` queries; mutations are blocked at the validator and connector level.
- **No stack traces in responses** — Global exception handler returns sanitized error messages. DSN strings are stripped from PostgreSQL error messages before they leave the connector.
- **UUID primary keys** — All tables use UUID PKs. No sequential integer IDs exposed.
- **Auth via Clerk** — JWT verification on all protected routes.

---

## Build Phases

| Phase | Status | What was built |
|---|---|---|
| Phase 1 — Foundation | Done | Docker, DB, FastAPI, Redis, Celery, all route stubs |
| Phase 2 — Connectors | Done | PostgreSQL connector, encryption, connection CRUD, schema API |
| Phase 3 — Schema Brain | Done | pgvector indexing, Claude descriptions, cosine similarity search |
| Phase 4 — Sessions | Done | Session management, message persistence, session summary |
| Phase 5 — Agents | Done | Orchestrator + SQL + Analyst + Schema agents, full pipeline |
| Phase 6 — Output Layer | Done | Output agent, report/deck generation stubs |
| Phase 7 — Frontend | Done | Next.js, chat UI, analysis canvas, charts, connection management |
| Senior Analyst Upgrade | Done | Statistics engine, viz recommender, multi-step pipeline, SSE streaming |
| Phase 8 — Proactive Agent | Stub | Interface defined, feature-flagged off |

---

## Example Output

Given the question: *"Which agent type has the highest average latency and how many calls has it made?"*

**Analysis Plan (auto-generated)**
```
Step 1: Aggregate agent_logs by agent_type — compute AVG(latency_ms), COUNT(*), MAX(latency_ms)
```

**SQL Generated**
```sql
WITH agent_stats AS (
    SELECT
        agent_type,
        AVG(latency_ms)                                          AS avg_latency_ms,
        COUNT(*)                                                 AS total_calls,
        MAX(latency_ms)                                          AS max_latency_ms,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) AS median_latency_ms
    FROM agent_logs
    GROUP BY agent_type
)
SELECT *
FROM agent_stats
ORDER BY avg_latency_ms DESC
LIMIT 10000;
```

**Statistical Analysis**
- Profile: 4 rows, 4 columns
- Group comparison: Welch t-test between agent types (p=0.03, significant)

**Visualizations**
- Bar chart: avg_latency_ms by agent_type (sorted descending)
- Stat cards: sum / mean / max for avg_latency_ms and total_calls

**Analyst Narrative**
> schema_brain leads all agent types with an average latency of 412ms across 13 calls — 2.8x higher than the next highest agent (sql_agent at 148ms). The high latency is attributable to the dual LLM calls schema_brain makes per table during indexing. The remaining agents (analyst_agent, orchestrator) cluster between 95–148ms with >35 calls each, suggesting normal operational performance. Recommended next: investigate schema_brain call distribution — a P95 analysis may reveal a long tail from large schemas driving the average up.

---

## Contributing

1. All DB calls must be async — `await db.execute(select(...))`
2. Never use `os.environ` directly — always `from app.core.config import settings`
3. Every LLM call must be logged to `agent_logs`
4. Credentials are never stored or logged in plaintext
5. Every new router must be registered in `app/main.py`
6. UUID primary keys everywhere — no integer IDs
