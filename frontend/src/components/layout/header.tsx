"use client";
import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function Header({ title, description, actions, className }: HeaderProps) {
  return (
    <div className={cn("flex h-14 items-center justify-between border-b bg-background px-6", className)}>
      <div>
        <h1 className="text-base font-semibold">{title}</h1>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
