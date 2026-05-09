import { api } from "./client";
import type {
  ConnectionCreate,
  ConnectionTestResult,
  DataConnection,
} from "@/types";

export const connectionsApi = {
  list: () => api.get<DataConnection[]>("/connections/"),

  get: (id: string) => api.get<DataConnection>(`/connections/${id}`),

  create: (payload: ConnectionCreate) =>
    api.post<DataConnection>("/connections/", payload),

  update: (id: string, payload: Partial<ConnectionCreate>) =>
    api.put<DataConnection>(`/connections/${id}`, payload),

  delete: (id: string) => api.delete<void>(`/connections/${id}`),

  test: (id: string) =>
    api.post<ConnectionTestResult>(`/connections/${id}/test`, {}),
};
