import { create } from "zustand";
import type { DataConnection } from "@/types";

interface ConnectionStore {
  connections: DataConnection[];
  activeConnectionId: string | null;
  setConnections: (connections: DataConnection[]) => void;
  setActiveConnection: (id: string | null) => void;
  upsertConnection: (conn: DataConnection) => void;
  removeConnection: (id: string) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  connections: [],
  activeConnectionId: null,

  setConnections: (connections) => set({ connections }),

  setActiveConnection: (id) => set({ activeConnectionId: id }),

  upsertConnection: (conn) =>
    set((state) => {
      const exists = state.connections.find((c) => c.id === conn.id);
      return {
        connections: exists
          ? state.connections.map((c) => (c.id === conn.id ? conn : c))
          : [conn, ...state.connections],
      };
    }),

  removeConnection: (id) =>
    set((state) => ({
      connections: state.connections.filter((c) => c.id !== id),
      activeConnectionId:
        state.activeConnectionId === id ? null : state.activeConnectionId,
    })),
}));
