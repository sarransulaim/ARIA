// ── Connections ───────────────────────────────────────────────────────────────

export type ConnectorType =
  | "postgresql"
  | "mysql"
  | "snowflake"
  | "bigquery"
  | "csv";

export interface DataConnection {
  id: string;
  name: string;
  connector_type: ConnectorType;
  description: string | null;
  is_active: boolean;
  is_read_only: boolean;
  last_tested_at: string | null;
  schema_last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectionCreate {
  name: string;
  connector_type: ConnectorType;
  description?: string;
  connection_config: Record<string, unknown>;
  credentials: Record<string, unknown>;
  is_read_only?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  latency_ms: number;
  error: string | null;
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export type SessionStatus = "active" | "archived";

export interface Session {
  id: string;
  title: string;
  status: SessionStatus;
  connection_id: string;
  session_summary: string | null;
  key_findings: string[];
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  title: string;
  connection_id: string;
}

// ── Messages ──────────────────────────────────────────────────────────────────

export type MessageRole = "user" | "assistant";
export type MessageType =
  | "question"
  | "sql"
  | "result"
  | "analysis"
  | "proactive_insight"
  | "error";

export interface ChatMessage {
  id: string;
  session_id: string;
  role: MessageRole;
  message_type: MessageType;
  content: string;
  metadata: Record<string, unknown>;
  parent_message_id: string | null;
  created_at: string;
}

// ── Analysis ──────────────────────────────────────────────────────────────────

export interface ResultsPreview {
  columns: string[];
  rows: unknown[][];
}

export interface VisualizationConfig {
  chart_type: string;
  title?: string;
  x_axis?: string;
  y_axis?: string;
  color_by?: string;
  [key: string]: unknown;
}

export interface AnalysisResponse {
  message_id: string | null;
  sql_generated: string | null;
  sql_explanation: string | null;
  results_preview: ResultsPreview | null;
  row_count: number;
  analysis_narrative: string;
  suggested_followups: string[];
  visualization_config: VisualizationConfig | null;
  error: boolean;
}

export interface AnalysisRequest {
  question: string;
  session_id: string;
  connection_id: string;
}

// ── Query Executions ──────────────────────────────────────────────────────────

export interface QueryExecution {
  id: string;
  session_id: string;
  connection_id: string;
  sql_text: string;
  natural_language_prompt: string;
  status: "running" | "completed" | "failed";
  execution_time_ms: number | null;
  row_count: number | null;
  result_preview: ResultsPreview | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// ── Outputs ───────────────────────────────────────────────────────────────────

export interface ReportRequest {
  session_id: string;
  format: "pdf" | "docx";
  audience?: string;
  focus?: string;
}

export interface PresentationRequest {
  session_id: string;
  format: "pptx";
  audience?: string;
  focus?: string;
}

export interface OutputJob {
  report_id?: string;
  presentation_id?: string;
  status: string;
}

export interface ReportRecord {
  id: string;
  session_id: string;
  title: string;
  report_format: string;
  status: string;
  storage_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface PresentationRecord {
  id: string;
  session_id: string;
  title: string;
  pres_format: string;
  status: string;
  storage_key: string | null;
  google_slides_url: string | null;
  created_at: string;
  updated_at: string;
}

// ── UI state ──────────────────────────────────────────────────────────────────

export interface CanvasEntry {
  id: string;
  question: string;
  sql: string | null;
  sqlExplanation: string | null;
  results: ResultsPreview | null;
  rowCount: number;
  narrative: string;
  vizConfig: VisualizationConfig | null;
  error: boolean;
  timestamp: string;
}
