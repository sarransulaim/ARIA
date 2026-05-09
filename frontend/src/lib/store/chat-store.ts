import { create } from "zustand";
import type { AnalysisResponse, CanvasEntry } from "@/types";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isLoading?: boolean;
  isError?: boolean;
  analysisData?: AnalysisResponse;
}

interface ChatStore {
  messages: Record<string, ChatMessage[]>;
  canvasEntries: Record<string, CanvasEntry[]>;
  isAnalyzing: boolean;
  error: string | null;

  addMessage: (sessionId: string, message: ChatMessage) => void;
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  addCanvasEntry: (sessionId: string, entry: CanvasEntry) => void;
  setCanvasEntries: (sessionId: string, entries: CanvasEntry[]) => void;
  setAnalyzing: (value: boolean) => void;
  setError: (error: string | null) => void;
  clearSession: (sessionId: string) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: {},
  canvasEntries: {},
  isAnalyzing: false,
  error: null,

  addMessage: (sessionId, message) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: [...(state.messages[sessionId] ?? []), message],
      },
    })),

  setMessages: (sessionId, messages) =>
    set((state) => ({
      messages: { ...state.messages, [sessionId]: messages },
    })),

  addCanvasEntry: (sessionId, entry) =>
    set((state) => ({
      canvasEntries: {
        ...state.canvasEntries,
        [sessionId]: [...(state.canvasEntries[sessionId] ?? []), entry],
      },
    })),

  setCanvasEntries: (sessionId, entries) =>
    set((state) => ({
      canvasEntries: { ...state.canvasEntries, [sessionId]: entries },
    })),

  setAnalyzing: (value) => set({ isAnalyzing: value }),

  setError: (error) => set({ error }),

  clearSession: (sessionId) =>
    set((state) => {
      const { [sessionId]: _m, ...messages } = state.messages;
      const { [sessionId]: _c, ...canvasEntries } = state.canvasEntries;
      return { messages, canvasEntries };
    }),
}));
