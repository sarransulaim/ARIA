import { create } from "zustand";
import type { Session } from "@/types";

interface SessionStore {
  sessions: Session[];
  activeSession: Session | null;
  setSessions: (sessions: Session[]) => void;
  setActiveSession: (session: Session | null) => void;
  upsertSession: (session: Session) => void;
  removeSession: (id: string) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessions: [],
  activeSession: null,

  setSessions: (sessions) => set({ sessions }),

  setActiveSession: (session) => set({ activeSession: session }),

  upsertSession: (session) =>
    set((state) => {
      const exists = state.sessions.find((s) => s.id === session.id);
      return {
        sessions: exists
          ? state.sessions.map((s) => (s.id === session.id ? session : s))
          : [session, ...state.sessions],
        activeSession:
          state.activeSession?.id === session.id
            ? session
            : state.activeSession,
      };
    }),

  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      activeSession: state.activeSession?.id === id ? null : state.activeSession,
    })),
}));
