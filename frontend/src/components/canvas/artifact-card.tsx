"use client";
import {
  BarChart2,
  Table2,
  Code2,
  TrendingUp,
  Lightbulb,
  List,
  Hash,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { ResultsTable } from "./results-table";
import { SqlDisplay } from "./sql-display";
import type { AnalysisArtifact, ResultsPreview, VisualizationConfig } from "@/types";

interface ArtifactCardProps {
  artifact: AnalysisArtifact;
}

export function ArtifactCard({ artifact }: ArtifactCardProps) {
  switch (artifact.artifact_type) {
    case "query_plan":
      return <QueryPlanCard artifact={artifact} />;
    case "sql":
      return <SqlCard artifact={artifact} />;
    case "table":
      return <TableCard artifact={artifact} />;
    case "chart":
      return <ChartCard artifact={artifact} />;
    case "stat_card":
      return <StatCard artifact={artifact} />;
    case "statistics":
      return <StatisticsCard artifact={artifact} />;
    case "insights":
      return <InsightsCard artifact={artifact} />;
    default:
      return null;
  }
}

function QueryPlanCard({ artifact }: ArtifactCardProps) {
  const steps = (artifact.data.steps ?? []) as Array<{
    step: number;
    purpose: string;
  }>;
  const intent = artifact.data.intent as string | undefined;
  return (
    <div className="rounded-md border border-dashed bg-muted/20 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <List className="h-3 w-3" />
        Analysis Plan
        {intent && (
          <Badge variant="outline" className="ml-1 text-[10px]">
            {intent.replace(/_/g, " ")}
          </Badge>
        )}
      </div>
      <ol className="space-y-1">
        {steps.map((s) => (
          <li key={s.step} className="flex items-start gap-2 text-sm">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
              {s.step}
            </span>
            <span className="text-muted-foreground">{s.purpose}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function SqlCard({ artifact }: ArtifactCardProps) {
  const sql = artifact.data.sql as string;
  const explanation = artifact.data.explanation as string | undefined;
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Code2 className="h-3 w-3" />
        {artifact.title}
      </div>
      <SqlDisplay sql={sql} explanation={explanation} />
    </div>
  );
}

function TableCard({ artifact }: ArtifactCardProps) {
  const columns = (artifact.data.columns ?? []) as string[];
  const rows = (artifact.data.rows ?? []) as unknown[][];
  const rowCount = (artifact.data.row_count ?? rows.length) as number;
  const execMs = artifact.data.execution_time_ms as number | undefined;
  const results: ResultsPreview = { columns, rows };
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Table2 className="h-3 w-3" />
          {artifact.title}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{rowCount.toLocaleString()} rows</Badge>
          {execMs != null && (
            <span className="text-[10px]">{execMs}ms</span>
          )}
        </div>
      </div>
      <ResultsTable results={results} rowCount={rowCount} />
    </div>
  );
}

function ChartCard({ artifact }: ArtifactCardProps) {
  const config = artifact.data as unknown as VisualizationConfig;
  const columns = (config.data as unknown[])?.length
    ? [String(config.x_key ?? ""), ...(config.y_keys ?? [])]
    : [];
  const rows = ((config.data as unknown[]) ?? []).map((row) => {
    const r = row as Record<string, unknown>;
    return [
      r[String(config.x_key)] ?? "",
      ...(config.y_keys ?? []).map((k) => r[k] ?? ""),
    ];
  });
  const results: ResultsPreview = { columns, rows };
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        <BarChart2 className="h-3 w-3" />
        {artifact.title}
      </div>
      <ChartRenderer config={config} results={results} />
    </div>
  );
}

function StatCard({ artifact }: ArtifactCardProps) {
  const data = artifact.data as {
    sum?: number | null;
    mean?: number | null;
    max?: number | null;
    count?: number | null;
  };
  const fmt = (v: number | null | undefined) =>
    v == null ? "—" : v.toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <div className="rounded-md border bg-card p-3 text-center">
      <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
        <Hash className="h-3 w-3" />
        {artifact.title}
      </div>
      <div className="mt-1 text-2xl font-bold tabular-nums">{fmt(data.sum)}</div>
      <div className="mt-1 flex justify-center gap-3 text-[10px] text-muted-foreground">
        {data.mean != null && <span>avg {fmt(data.mean)}</span>}
        {data.max != null && <span>max {fmt(data.max)}</span>}
        {data.count != null && <span>n={data.count.toLocaleString()}</span>}
      </div>
    </div>
  );
}

function StatisticsCard({ artifact }: ArtifactCardProps) {
  const trend = artifact.data.trend as
    | { available: boolean; direction?: string; r_squared?: number; p_value?: number; slope_per_day?: number }
    | undefined;
  const corr = artifact.data.correlation as
    | { available: boolean; strong_pairs?: Array<{ col1: string; col2: string; r: number; strength: string }> }
    | undefined;
  const profile = artifact.data.profile as
    | { row_count: number; column_count: number }
    | undefined;

  if (!trend?.available && !corr?.available && !profile) return null;

  return (
    <div className="rounded-md border bg-muted/10 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <TrendingUp className="h-3 w-3" />
        Statistical Analysis
      </div>
      <div className="space-y-1.5 text-xs">
        {profile && (
          <div className="text-muted-foreground">
            {profile.row_count.toLocaleString()} rows · {profile.column_count} columns
          </div>
        )}
        {trend?.available && (
          <div>
            Trend:{" "}
            <span
              className={
                trend.direction === "up"
                  ? "font-medium text-green-600"
                  : trend.direction === "down"
                    ? "font-medium text-red-600"
                    : "text-muted-foreground"
              }
            >
              {trend.direction}
            </span>
            {trend.r_squared != null && (
              <span className="ml-1.5 text-muted-foreground">
                R²={trend.r_squared.toFixed(2)}
              </span>
            )}
            {trend.p_value != null && (
              <span className="ml-1.5 text-muted-foreground">
                p={trend.p_value < 0.001 ? "<0.001" : trend.p_value.toFixed(3)}
              </span>
            )}
          </div>
        )}
        {corr?.available && (corr.strong_pairs ?? []).length > 0 && (
          <div>
            Strong correlations:{" "}
            {(corr.strong_pairs ?? []).slice(0, 3).map((p) => (
              <Badge key={`${p.col1}-${p.col2}`} variant="outline" className="mr-1 text-[10px]">
                {p.col1} ↔ {p.col2} (r={p.r})
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function InsightsCard({ artifact }: ArtifactCardProps) {
  const insights = (artifact.data.insights ?? []) as string[];
  const anomalies = (artifact.data.anomalies ?? []) as string[];
  if (!insights.length && !anomalies.length) return null;
  return (
    <div className="rounded-md border bg-muted/10 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Lightbulb className="h-3 w-3" />
        Key Insights
      </div>
      <ul className="space-y-1.5">
        {insights.map((ins, i) => (
          <li key={i} className="flex items-start gap-1.5 text-sm">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
            {ins}
          </li>
        ))}
      </ul>
      {anomalies.length > 0 && (
        <div className="mt-2 space-y-1">
          <p className="text-[10px] font-medium uppercase tracking-wide text-amber-600">
            Anomalies
          </p>
          {anomalies.map((a, i) => (
            <p key={i} className="text-xs text-amber-700">
              ⚠ {a}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
