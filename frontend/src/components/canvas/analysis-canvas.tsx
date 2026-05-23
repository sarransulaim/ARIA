"use client";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart2, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArtifactCard } from "./artifact-card";
import { SqlDisplay } from "./sql-display";
import { formatRelative } from "@/lib/utils";
import { useChatStore } from "@/lib/store/chat-store";

interface AnalysisCanvasProps {
  sessionId: string;
}

export function AnalysisCanvas({ sessionId }: AnalysisCanvasProps) {
  const entries = useChatStore((s) => s.canvasEntries[sessionId] ?? []);
  const streaming = useChatStore((s) => s.streaming);

  if (!entries.length && !streaming.isStreaming) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
        <BarChart2 className="h-12 w-12 opacity-20" />
        <p className="text-sm">Analysis results will appear here</p>
        <p className="text-xs">Ask a question in the chat to get started</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-4">
        {/* Live streaming progress */}
        {streaming.isStreaming && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-primary/20 bg-card p-4 shadow-sm"
          >
            <div className="mb-2 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm font-medium">
                {streaming.currentPlan?.title ?? "Analysing…"}
              </span>
            </div>
            <Progress value={streaming.progressPct} className="h-1.5" />
            <p className="mt-1.5 text-xs text-muted-foreground">
              {streaming.progressMessage}
            </p>
            {/* Show plan steps if available */}
            {streaming.currentPlan && (
              <ol className="mt-3 space-y-1">
                {streaming.currentPlan.steps.map((s) => {
                  const stepData = streaming.streamingSteps.get(s.step);
                  return (
                    <li key={s.step} className="flex items-center gap-2 text-xs">
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                        {s.step}
                      </span>
                      <span className={stepData?.result ? "text-foreground" : "text-muted-foreground"}>
                        {s.purpose}
                      </span>
                      {stepData?.result && (
                        <Badge variant="secondary" className="ml-auto text-[10px]">
                          {stepData.result.row_count.toLocaleString()} rows
                        </Badge>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
            {/* Show SQL as it arrives */}
            {streaming.streamingSteps.size > 0 && (
              <div className="mt-3 space-y-2">
                {Array.from(streaming.streamingSteps.entries()).map(([step, data]) =>
                  data.sql ? (
                    <SqlDisplay key={step} sql={data.sql} collapsed />
                  ) : null,
                )}
              </div>
            )}
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {entries.map((entry) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-lg border bg-card shadow-sm"
            >
              {/* Entry header */}
              <div className="flex items-start justify-between gap-2 border-b p-4">
                <div className="flex flex-wrap items-start gap-2">
                  {entry.error ? (
                    <Badge variant="destructive">Error</Badge>
                  ) : (
                    <>
                      <Badge variant="secondary">
                        {entry.rowCount.toLocaleString()} rows
                      </Badge>
                      {entry.analysisType && (
                        <Badge variant="outline" className="text-[10px]">
                          {entry.analysisType.replace(/_/g, " ")}
                        </Badge>
                      )}
                    </>
                  )}
                  <p className="text-sm font-medium">
                    {entry.analysisTitle ?? entry.question}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelative(entry.timestamp)}
                </span>
              </div>

              <div className="space-y-4 p-4">
                {/* Narrative — always first */}
                {entry.narrative && (
                  <div className="flex gap-2 rounded-md bg-muted/30 p-3">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <p className="text-sm leading-relaxed">{entry.narrative}</p>
                  </div>
                )}

                {/* Stat cards row */}
                {entry.artifacts.filter((a) => a.artifact_type === "stat_card").length > 0 && (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {entry.artifacts
                      .filter((a) => a.artifact_type === "stat_card")
                      .map((a, i) => (
                        <ArtifactCard key={i} artifact={a} />
                      ))}
                  </div>
                )}

                {/* All other artifacts in order */}
                {entry.artifacts
                  .filter((a) => a.artifact_type !== "stat_card")
                  .map((artifact, i) => (
                    <ArtifactCard key={i} artifact={artifact} />
                  ))}

                {/* Follow-up suggestions */}
                {entry.artifacts.length === 0 && (
                  <>
                    {entry.sql && (
                      <SqlDisplay
                        sql={entry.sql}
                        explanation={entry.sqlExplanation ?? undefined}
                      />
                    )}
                  </>
                )}
              </div>

              {/* Follow-up footer */}
              {entry.queryPlan.length > 0 && entry.queryPlan[0] !== entry.question && (
                <div className="border-t px-4 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    Analysis steps
                  </p>
                  <ol className="mt-1 space-y-0.5">
                    {entry.queryPlan.map((step, i) => (
                      <li key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <span className="font-medium">{i + 1}.</span> {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ScrollArea>
  );
}
