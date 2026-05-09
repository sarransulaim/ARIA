"use client";
import { motion } from "framer-motion";
import { Bot, User, Lightbulb, AlertCircle } from "lucide-react";
import { cn, formatRelative } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isLoading?: boolean;
  isError?: boolean;
  suggestedFollowups?: string[];
  onFollowup?: (question: string) => void;
}

export function MessageBubble({
  role,
  content,
  timestamp,
  isLoading,
  isError,
  suggestedFollowups,
  onFollowup,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-2.5", isUser && "flex-row-reverse")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-aria-600" : "bg-muted border",
        )}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-white" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-aria-600" />
        )}
      </div>

      <div className={cn("max-w-[80%]", isUser && "items-end flex flex-col")}>
        {/* Bubble */}
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "bg-aria-600 text-white rounded-tr-sm"
              : isError
              ? "bg-red-50 border border-red-200 text-red-700 rounded-tl-sm"
              : "bg-muted rounded-tl-sm",
          )}
        >
          {isLoading ? (
            <span className="flex gap-1">
              <span className="animate-bounce" style={{ animationDelay: "0ms" }}>•</span>
              <span className="animate-bounce" style={{ animationDelay: "150ms" }}>•</span>
              <span className="animate-bounce" style={{ animationDelay: "300ms" }}>•</span>
            </span>
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
          )}
        </div>

        {/* Timestamp */}
        <span className="mt-1 px-1 text-[10px] text-muted-foreground">
          {formatRelative(timestamp)}
        </span>

        {/* Follow-ups */}
        {suggestedFollowups && suggestedFollowups.length > 0 && onFollowup && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {suggestedFollowups.map((q) => (
              <button
                key={q}
                onClick={() => onFollowup(q)}
                className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-aria-300 hover:text-aria-600"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
