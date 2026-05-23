"use client";
import { useCallback, useRef } from "react";
import { queriesApi } from "@/lib/api/queries";
import { useChatStore } from "@/lib/store/chat-store";
import type { CanvasEntry, StreamEventPlan, StreamEventResult } from "@/types";

interface UseAnalysisProps {
  sessionId: string;
  connectionId: string;
}

export function useAnalysis({ sessionId, connectionId }: UseAnalysisProps) {
  const {
    addMessage,
    updateMessage,
    addCanvasEntry,
    setAnalyzing,
    setError,
    setStreaming,
  } = useChatStore();

  const abortRef = useRef<AbortController | null>(null);

  const submitQuestion = useCallback(
    async (question: string) => {
      // Cancel any in-progress stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

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
      setStreaming({
        isStreaming: true,
        progressPct: 0,
        progressMessage: "Starting…",
        currentPlan: null,
        streamingSteps: new Map(),
      });

      try {
        const streamingSteps = new Map<
          number,
          { sql?: string; result?: StreamEventResult }
        >();

        for await (const event of queriesApi.streamAnalysis(
          { question, session_id: sessionId, connection_id: connectionId },
          controller.signal,
        )) {
          switch (event.type) {
            case "progress":
              setStreaming({
                progressPct: event.pct,
                progressMessage: event.message,
              });
              updateMessage(sessionId, assistantMsgId, {
                content: event.message,
              });
              break;

            case "plan":
              setStreaming({ currentPlan: event as StreamEventPlan });
              break;

            case "sql":
              streamingSteps.set(event.step, {
                ...streamingSteps.get(event.step),
                sql: event.sql,
              });
              setStreaming({ streamingSteps: new Map(streamingSteps) });
              break;

            case "result":
              streamingSteps.set(event.step, {
                ...streamingSteps.get(event.step),
                result: event as StreamEventResult,
              });
              setStreaming({ streamingSteps: new Map(streamingSteps) });
              break;

            case "narrative":
              updateMessage(sessionId, assistantMsgId, {
                content: event.narrative,
              });
              break;

            case "done": {
              const r = event.response;
              updateMessage(sessionId, assistantMsgId, {
                content: r.analysis_narrative,
                isLoading: false,
                isError: r.error,
                analysisData: r,
              });

              if (!r.error) {
                const entry: CanvasEntry = {
                  id: crypto.randomUUID(),
                  question,
                  sql: r.sql_generated,
                  sqlExplanation: r.sql_explanation,
                  results: r.results_preview,
                  rowCount: r.row_count,
                  narrative: r.analysis_narrative,
                  vizConfig: r.visualization_config,
                  error: r.error,
                  timestamp: now,
                  analysisType: r.analysis_type,
                  analysisTitle: r.analysis_title,
                  artifacts: r.artifacts,
                  keyInsights: r.key_insights,
                  statisticalSummary: r.statistical_summary,
                  dataQualityWarnings: r.data_quality_warnings,
                  queryPlan: r.query_plan,
                  allCharts: r.all_charts,
                  allStepResults: r.all_step_results,
                };
                addCanvasEntry(sessionId, entry);
              }
              break;
            }

            case "error": {
              const msg = event.message ?? "Analysis failed";
              updateMessage(sessionId, assistantMsgId, {
                content: msg,
                isLoading: false,
                isError: true,
              });
              setError(msg);
              break;
            }
          }
        }
      } catch (err) {
        if ((err as Error)?.name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Unexpected error";
        updateMessage(sessionId, assistantMsgId, {
          content: message,
          isLoading: false,
          isError: true,
        });
        setError(message);
      } finally {
        setAnalyzing(false);
        setStreaming({
          isStreaming: false,
          progressPct: 100,
          progressMessage: "",
          currentPlan: null,
          streamingSteps: new Map(),
        });
      }
    },
    [
      sessionId,
      connectionId,
      addMessage,
      updateMessage,
      addCanvasEntry,
      setAnalyzing,
      setError,
      setStreaming,
    ],
  );

  return { submitQuestion };
}
