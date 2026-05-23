"use client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ResultsPreview, VisualizationConfig } from "@/types";

interface ChartRendererProps {
  config: VisualizationConfig;
  results: ResultsPreview;
}

const COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e", "#8b5cf6"];

function buildDataFromResults(results: ResultsPreview): Record<string, unknown>[] {
  const { columns, rows } = results;
  return rows.map((row) => {
    const obj: Record<string, unknown> = {};
    columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}

function normalize(config: VisualizationConfig): {
  chartType: string;
  xKey: string;
  yKeys: string[];
  title: string | undefined;
} {
  // New format: type, x_key, y_keys
  if (config.type && config.x_key) {
    return {
      chartType: config.type,
      xKey: config.x_key,
      yKeys: config.y_keys ?? [],
      title: config.title,
    };
  }
  // Legacy format: chart_type, x_axis, y_axis
  return {
    chartType: config.chart_type ?? "bar",
    xKey: config.x_axis ?? "",
    yKeys: config.y_axis ? [config.y_axis] : [],
    title: config.title,
  };
}

export function ChartRenderer({ config, results }: ChartRendererProps) {
  const { chartType, xKey, yKeys, title } = normalize(config);

  // Prefer data embedded in config (new format) over building from results
  const rawData =
    Array.isArray(config.data) && config.data.length
      ? (config.data as Record<string, unknown>[])
      : buildDataFromResults(results);

  if (!rawData.length || !xKey || !yKeys.length) {
    return (
      <div className="flex h-48 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
        Insufficient data to render chart
      </div>
    );
  }

  return (
    <div className="w-full">
      {title && <p className="mb-2 text-center text-sm font-medium">{title}</p>}
      <ResponsiveContainer width="100%" height={280}>
        {chartType === "line" ? (
          <LineChart data={rawData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((k, i) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        ) : chartType === "area" ? (
          <AreaChart data={rawData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((k, i) => (
              <Area
                key={k}
                type="monotone"
                dataKey={k}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length] + "33"}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        ) : chartType === "scatter" ? (
          <ScatterChart>
            <CartesianGrid />
            <XAxis dataKey={xKey} name={xKey} tick={{ fontSize: 11 }} />
            <YAxis dataKey={yKeys[0]} name={yKeys[0]} tick={{ fontSize: 11 }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={rawData} fill={COLORS[0]} />
          </ScatterChart>
        ) : chartType === "bar_horizontal" ? (
          <BarChart data={rawData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis dataKey={xKey} type="category" tick={{ fontSize: 11 }} width={100} />
            <Tooltip />
            <Legend />
            {yKeys.map((k, i) => (
              <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[0, 4, 4, 0]} />
            ))}
          </BarChart>
        ) : (
          // bar, bar_grouped, and fallback
          <BarChart data={rawData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {yKeys.map((k, i) => (
              <Bar
                key={k}
                dataKey={k}
                fill={COLORS[i % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
