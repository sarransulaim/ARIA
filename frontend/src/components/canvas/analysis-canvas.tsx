"use client";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart2, Table2, FileText, Lightbulb } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChartRenderer } from "@/components/charts/chart-renderer";
import { ResultsTable } from "./results-table";
import { SqlDisplay } from "./sql-display";
import { formatRelative } from "@/lib/utils";
import { useChatStore } from "@/lib/store/chat-store";

interface AnalysisCanvasProps {
  sessionId: string;
}

export function AnalysisCanvas({ sessionId }: AnalysisCanvasProps) {
  const entries = useChatStore((s) => s.canvasEntries[sessionId] ?? []);

  if (!entries.length) {
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
                <div className="flex items-start gap-2">
                  {entry.error ? (
                    <Badge variant="destructive">Error</Badge>
                  ) : (
                    <Badge variant="secondary">
                      {entry.rowCount.toLocaleString()} rows
                    </Badge>
                  )}
                  <p className="text-sm font-medium">{entry.question}</p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelative(entry.timestamp)}
                </span>
              </div>

              <div className="space-y-4 p-4">
                {/* SQL */}
                {entry.sql && (
                  <SqlDisplay sql={entry.sql} explanation={entry.sqlExplanation ?? undefined} />
                )}

                {/* Narrative */}
                {entry.narrative && (
                  <div className="flex gap-2 rounded-md bg-muted/30 p-3">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <p className="text-sm leading-relaxed">{entry.narrative}</p>
                  </div>
                )}

                {/* Chart */}
                {entry.vizConfig && entry.results && (
                  <div className="rounded-md border p-3">
                    <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                      <BarChart2 className="h-3 w-3" />
                      Visualization
                    </div>
                    <ChartRenderer config={entry.vizConfig} results={entry.results} />
                  </div>
                )}

                {/* Results table */}
                {entry.results && !entry.error && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Table2 className="h-3 w-3" />
                      Query Results
                    </div>
                    <ResultsTable results={entry.results} rowCount={entry.rowCount} />
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ScrollArea>
  );
}
