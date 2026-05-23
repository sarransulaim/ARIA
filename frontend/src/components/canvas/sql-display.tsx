"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { Copy, Check, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false, loading: () => <div className="h-32 animate-pulse bg-muted rounded" /> },
);

interface SqlDisplayProps {
  sql: string;
  explanation?: string;
  collapsed?: boolean;
}

export function SqlDisplay({ sql, explanation, collapsed: initialCollapsed = false }: SqlDisplayProps) {
  const [copied, setCopied] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md border bg-[#1e1e1e] overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
        <button
          className="flex items-center gap-1.5 text-xs font-mono text-white/50 uppercase tracking-wider hover:text-white/80 transition-colors"
          onClick={() => setIsCollapsed((v) => !v)}
        >
          {isCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          SQL
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-white/50 hover:text-white hover:bg-white/10"
          onClick={handleCopy}
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
      {!isCollapsed && (
        <>
          <MonacoEditor
            height={Math.min(32 + sql.split("\n").length * 19, 300)}
            language="sql"
            value={sql}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              fontSize: 12,
              lineNumbers: "off",
              folding: false,
              renderLineHighlight: "none",
              overviewRulerBorder: false,
              hideCursorInOverviewRuler: true,
              padding: { top: 8, bottom: 8 },
              scrollbar: { vertical: "hidden", horizontal: "auto" },
            }}
            theme="vs-dark"
          />
          {explanation && (
            <div className="border-t border-white/10 px-3 py-2">
              <p className="text-xs text-white/60">{explanation}</p>
            </div>
          )}
        </>
      )}
      {isCollapsed && (
        <div className="px-3 py-1.5">
          <p className="truncate text-xs font-mono text-white/40">{sql.slice(0, 80)}…</p>
        </div>
      )}
    </div>
  );
}
