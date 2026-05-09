import { api } from "./client";
import type { AnalysisRequest, AnalysisResponse, QueryExecution } from "@/types";

export const queriesApi = {
  analyze: (payload: AnalysisRequest) =>
    api.post<AnalysisResponse>("/analysis/", payload),

  getHistory: (sessionId: string) =>
    api.get<QueryExecution[]>(`/analysis/${sessionId}/history`),

  getExecution: (executionId: string) =>
    api.get<QueryExecution>(`/analysis/execution/${executionId}`),
};
