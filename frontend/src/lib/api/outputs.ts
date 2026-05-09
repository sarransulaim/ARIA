import { api } from "./client";
import type {
  OutputJob,
  PresentationRecord,
  PresentationRequest,
  ReportRecord,
  ReportRequest,
} from "@/types";

interface SessionOutputs {
  reports: ReportRecord[];
  presentations: PresentationRecord[];
}

export const outputsApi = {
  createReport: (payload: ReportRequest) =>
    api.post<OutputJob>("/outputs/report", payload),

  getReport: (id: string) => api.get<ReportRecord>(`/outputs/report/${id}`),

  downloadReportUrl: (id: string) => `/api/aria/outputs/report/${id}/download`,

  createPresentation: (payload: PresentationRequest) =>
    api.post<OutputJob>("/outputs/presentation", payload),

  getPresentation: (id: string) =>
    api.get<PresentationRecord>(`/outputs/presentation/${id}`),

  downloadPresentationUrl: (id: string) =>
    `/api/aria/outputs/presentation/${id}/download`,

  listSessionOutputs: (sessionId: string) =>
    api.get<SessionOutputs>(`/outputs/session/${sessionId}`),
};
