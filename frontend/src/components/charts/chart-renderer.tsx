"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
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

function buildData(results: ResultsPreview): Record<string, unknown>[] {
  const { columns, rows } = results;
  return rows.map((row) => {
    const obj: Record<string, unknown> = {};
    columns.forEach((col, i) => { obj[col] = row[i]; });
    return obj;
  });
}

export function ChartRenderer({ config, results }: ChartRendererProps) {
  const data = buildData(results);
  const { chart_type, x_axis = "", y_axis = "", title } = config;

  if (!data.length || !x_axis || !y_axis) {
    return (
      <div className="flex h-48 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
        Insufficient data to render chart
      </div>
    );
  }

  return (
    <div className="w-full">
      {title && <p className="mb-2 text-sm font-medium text-center">{title}</p>}
      <ResponsiveContainer width="100%" height={280}>
        {chart_type === "line" ? (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={x_axis} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey={y_axis} stroke={COLORS[0]} strokeWidth={2} dot={false} />
          </LineChart>
        ) : chart_type === "pie" ? (
          <PieChart>
            <Pie data={data} dataKey={y_axis} nameKey={x_axis} cx="50%" cy="50%" outerRadius={110} label>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        ) : chart_type === "scatter" ? (
          <ScatterChart>
            <CartesianGrid />
            <XAxis dataKey={x_axis} name={x_axis} tick={{ fontSize: 11 }} />
            <YAxis dataKey={y_axis} name={y_axis} tick={{ fontSize: 11 }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill={COLORS[0]} />
          </ScatterChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={x_axis} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey={y_axis} fill={COLORS[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
