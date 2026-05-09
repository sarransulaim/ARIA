"use client";
import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { QueryInput } from "./query-input";
import { useChatStore } from "@/lib/store/chat-store";
import { useAnalysis } from "@/hooks/use-analysis";

interface ChatPanelProps {
  sessionId: string;
  connectionId: string;
}

export function ChatPanel({ sessionId, connectionId }: ChatPanelProps) {
  const messages = useChatStore((s) => s.messages[sessionId] ?? []);
  const isAnalyzing = useChatStore((s) => s.isAnalyzing);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { submitQuestion } = useAnalysis({ sessionId, connectionId });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleFollowup = (question: string) => {
    submitQuestion(question);
  };

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 px-4 py-4">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-sm font-medium text-muted-foreground">
                Welcome to your analysis session
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Ask any question about your connected data
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
              isLoading={msg.isLoading}
              isError={msg.isError}
              suggestedFollowups={
                msg.analysisData?.suggested_followups ?? undefined
              }
              onFollowup={handleFollowup}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="border-t p-4">
        <QueryInput onSubmit={submitQuestion} isLoading={isAnalyzing} />
        <p className="mt-2 text-center text-[10px] text-muted-foreground">
          Every SQL query is shown to you for full transparency · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
