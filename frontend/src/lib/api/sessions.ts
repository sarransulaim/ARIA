import { api } from "./client";
import type { ChatMessage, Session, SessionCreate } from "@/types";

export const sessionsApi = {
  list: () => api.get<Session[]>("/sessions/"),

  get: (id: string) => api.get<Session>(`/sessions/${id}`),

  create: (payload: SessionCreate) =>
    api.post<Session>("/sessions/", payload),

  update: (id: string, payload: { title?: string }) =>
    api.put<Session>(`/sessions/${id}`, payload),

  archive: (id: string) => api.put<Session>(`/sessions/${id}/archive`, {}),

  getMessages: (id: string) =>
    api.get<ChatMessage[]>(`/sessions/${id}/messages`),
};
