"use client";
import { useState, useRef, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onSubmit: (question: string) => Promise<void>;
  isLoading: boolean;
  placeholder?: string;
}

export function QueryInput({ onSubmit, isLoading, placeholder }: QueryInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async () => {
    const q = value.trim();
    if (!q || isLoading) return;
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSubmit(q);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex items-end gap-2 rounded-xl border bg-background p-2 shadow-sm focus-within:ring-2 focus-within:ring-aria-500 focus-within:ring-offset-1">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        rows={1}
        disabled={isLoading}
        placeholder={placeholder ?? "Ask a question about your data…"}
        className={cn(
          "flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50",
          "min-h-[36px] max-h-[160px] py-1.5 px-1",
        )}
      />
      <Button
        size="icon"
        onClick={handleSubmit}
        disabled={!value.trim() || isLoading}
        className="h-9 w-9 shrink-0 bg-aria-600 hover:bg-aria-700"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
