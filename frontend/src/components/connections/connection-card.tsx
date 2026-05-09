"use client";
import { useState } from "react";
import { Database, Loader2, CheckCircle, XCircle, Trash2, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { connectionsApi } from "@/lib/api/connections";
import { useConnectionStore } from "@/lib/store/connection-store";
import { formatRelative } from "@/lib/utils";
import type { DataConnection } from "@/types";

interface ConnectionCardProps {
  connection: DataConnection;
  onSelect?: (id: string) => void;
  selected?: boolean;
}

export function ConnectionCard({ connection, onSelect, selected }: ConnectionCardProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency_ms: number } | null>(null);
  const { upsertConnection, removeConnection } = useConnectionStore();

  const handleTest = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setTesting(true);
    setTestResult(null);
    try {
      const result = await connectionsApi.test(connection.id);
      setTestResult(result);
      if (result.success) {
        upsertConnection({ ...connection, last_tested_at: new Date().toISOString() });
      }
    } catch {
      setTestResult({ success: false, latency_ms: 0 });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete connection "${connection.name}"?`)) return;
    try {
      await connectionsApi.delete(connection.id);
      removeConnection(connection.id);
    } catch {
      // ignore
    }
  };

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${selected ? "ring-2 ring-aria-500" : ""}`}
      onClick={() => onSelect?.(connection.id)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-md bg-aria-100 p-1.5">
              <Database className="h-4 w-4 text-aria-600" />
            </div>
            <div>
              <p className="text-sm font-semibold">{connection.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{connection.connector_type}</p>
              {connection.last_tested_at && (
                <p className="text-xs text-muted-foreground">
                  Tested {formatRelative(connection.last_tested_at)}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            {testResult && (
              testResult.success ? (
                <Badge variant="success" className="text-xs">
                  <CheckCircle className="mr-1 h-3 w-3" />
                  {testResult.latency_ms}ms
                </Badge>
              ) : (
                <Badge variant="destructive" className="text-xs">
                  <XCircle className="mr-1 h-3 w-3" />
                  Failed
                </Badge>
              )
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleTest} disabled={testing}>
                  {testing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>Test connection</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={handleDelete}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete</TooltipContent>
            </Tooltip>
          </div>
        </div>
        {connection.schema_last_indexed_at && (
          <p className="mt-2 text-xs text-emerald-600">
            Schema indexed {formatRelative(connection.schema_last_indexed_at)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
