import { api } from "./client";
import type {
  AnalysisRequest,
  AnalysisResponse,
  QueryExecution,
  StreamEvent,
} from "@/types";

const BASE = "/api/aria";

export const queriesApi = {
  analyze: (payload: AnalysisRequest) =>
    api.post<AnalysisResponse>("/analysis/", payload),

  streamAnalysis: async function* (
    payload: AnalysisRequest,
    signal?: AbortSignal,
  ): AsyncGenerator<StreamEvent> {
    const res = await fetch(`${BASE}/analysis/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok || !res.body) {
      const text = await res.text().catch(() => `HTTP ${res.status}`);
      throw new Error(text);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") return;
          try {
            yield JSON.parse(data) as StreamEvent;
          } catch {
            // skip malformed lines
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  getHistory: (sessionId: string) =>
    api.get<QueryExecution[]>(`/analysis/${sessionId}/history`),

  getExecution: (executionId: string) =>
    api.get<QueryExecution>(`/analysis/execution/${executionId}`),
};
