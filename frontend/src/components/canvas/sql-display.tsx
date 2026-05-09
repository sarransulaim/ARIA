"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false, loading: () => <div className="h-32 animate-pulse bg-muted rounded" /> },
);

interface SqlDisplayProps {
  sql: string;
  explanation?: string;
}

export function SqlDisplay({ sql, explanation }: SqlDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-md border bg-[#1e1e1e] overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
        <span className="text-xs font-mono text-white/50 uppercase tracking-wider">SQL</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-white/50 hover:text-white hover:bg-white/10"
          onClick={handleCopy}
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
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
    </div>
  );
}
