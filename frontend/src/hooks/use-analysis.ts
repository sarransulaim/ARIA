"use client";
import { useCallback } from "react";
import { queriesApi } from "@/lib/api/queries";
import { useChatStore } from "@/lib/store/chat-store";
import type { CanvasEntry } from "@/types";

interface UseAnalysisProps {
  sessionId: string;
  connectionId: string;
}

export function useAnalysis({ sessionId, connectionId }: UseAnalysisProps) {
  const { addMessage, addCanvasEntry, setAnalyzing, setError } = useChatStore();

  const submitQuestion = useCallback(
    async (question: string) => {
      const userMsgId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();
      const now = new Date().toISOString();

      addMessage(sessionId, {
        id: userMsgId,
        role: "user",
        content: question,
        timestamp: now,
      });
      addMessage(sessionId, {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        timestamp: now,
        isLoading: true,
      });

      setAnalyzing(true);
      setError(null);

      try {
        const result = await queriesApi.analyze({
          question,
          session_id: sessionId,
          connection_id: connectionId,
        });

        const store = useChatStore.getState();
        const msgs = store.messages[sessionId] ?? [];
        useChatStore.setState({
          messages: {
            ...store.messages,
            [sessionId]: msgs.map((m) =>
              m.id === assistantMsgId
                ? {
                    ...m,
                    content: result.analysis_narrative,
                    isLoading: false,
                    isError: result.error,
                    analysisData: result,
                  }
                : m,
            ),
          },
        });

        if (!result.error) {
          const entry: CanvasEntry = {
            id: crypto.randomUUID(),
            question,
            sql: result.sql_generated,
            sqlExplanation: result.sql_explanation,
            results: result.results_preview,
            rowCount: result.row_count,
            narrative: result.analysis_narrative,
            vizConfig: result.visualization_config,
            error: result.error,
            timestamp: now,
          };
          addCanvasEntry(sessionId, entry);
        }
      } catch (err) {
        const store = useChatStore.getState();
        const msgs = store.messages[sessionId] ?? [];
        const message = err instanceof Error ? err.message : "Unexpected error";
        useChatStore.setState({
          messages: {
            ...store.messages,
            [sessionId]: msgs.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: message, isLoading: false, isError: true }
                : m,
            ),
          },
          error: message,
        });
      } finally {
        setAnalyzing(false);
      }
    },
    [sessionId, connectionId, addMessage, addCanvasEntry, setAnalyzing, setError],
  );

  return { submitQuestion };
}
