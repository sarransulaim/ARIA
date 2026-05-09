"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Download, FileText, Presentation } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChatPanel } from "@/components/chat/chat-panel";
import { AnalysisCanvas } from "@/components/canvas/analysis-canvas";
import { sessionsApi } from "@/lib/api/sessions";
import { outputsApi } from "@/lib/api/outputs";
import { useSessionStore } from "@/lib/store/session-store";
import type { Session } from "@/types";

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

export default function SessionPage({ params }: PageProps) {
  const { sessionId } = use(params);
  const router = useRouter();
  const { activeSession, setActiveSession } = useSessionStore();
  const [isLoading, setIsLoading] = useState(!activeSession);
  const [generatingOutput, setGeneratingOutput] = useState(false);

  useEffect(() => {
    if (activeSession?.id !== sessionId) {
      setIsLoading(true);
      sessionsApi.get(sessionId).then((s) => {
        setActiveSession(s);
        setIsLoading(false);
      }).catch(() => {
        router.push("/sessions");
      });
    } else {
      setIsLoading(false);
    }
  }, [sessionId]);

  const session = activeSession?.id === sessionId ? activeSession : null;

  const handleExport = async (type: "docx" | "pdf" | "pptx") => {
    if (!session) return;
    setGeneratingOutput(true);
    try {
      if (type === "pptx") {
        const job = await outputsApi.createPresentation({
          session_id: sessionId,
          format: "pptx",
        });
        if (job.presentation_id) {
          window.open(outputsApi.downloadPresentationUrl(job.presentation_id), "_blank");
        }
      } else {
        const job = await outputsApi.createReport({
          session_id: sessionId,
          format: type,
        });
        if (job.report_id) {
          window.open(outputsApi.downloadReportUrl(job.report_id), "_blank");
        }
      }
    } finally {
      setGeneratingOutput(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex h-14 items-center gap-3 border-b px-4">
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="flex flex-1 gap-0">
          <div className="w-[380px] border-r p-4 space-y-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
          </div>
          <div className="flex-1 p-4">
            <Skeleton className="h-48 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push("/sessions")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-sm font-semibold">{session.title}</h1>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" disabled={generatingOutput}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Export
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleExport("docx")}>
              <FileText className="mr-2 h-4 w-4" />
              Word Document (.docx)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport("pdf")}>
              <FileText className="mr-2 h-4 w-4" />
              PDF Report (.pdf)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleExport("pptx")}>
              <Presentation className="mr-2 h-4 w-4" />
              Presentation (.pptx)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Workspace: Chat (left) + Canvas (right) */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex w-[380px] shrink-0 flex-col border-r">
          <ChatPanel sessionId={sessionId} connectionId={session.connection_id} />
        </div>
        <div className="flex-1 overflow-hidden bg-muted/10">
          <AnalysisCanvas sessionId={sessionId} />
        </div>
      </div>
    </div>
  );
}
