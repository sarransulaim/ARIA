"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, MessageSquare, Calendar, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/layout/header";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSessions } from "@/hooks/use-sessions";
import { useConnections } from "@/hooks/use-connections";
import { sessionsApi } from "@/lib/api/sessions";
import { useSessionStore } from "@/lib/store/session-store";
import { formatRelative } from "@/lib/utils";

export default function SessionsPage() {
  const router = useRouter();
  const { sessions, isLoading } = useSessions();
  const { connections } = useConnections();
  const upsertSession = useSessionStore((s) => s.upsertSession);

  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [connectionId, setConnectionId] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !connectionId) return;
    setCreating(true);
    try {
      const session = await sessionsApi.create({ title, connection_id: connectionId });
      upsertSession(session);
      setShowCreate(false);
      setTitle("");
      setConnectionId("");
      router.push(`/sessions/${session.id}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Analysis Sessions"
        description="Your workspaces for data exploration"
        actions={
          <Button size="sm" onClick={() => setShowCreate(true)} disabled={connections.length === 0}>
            <Plus className="mr-1.5 h-4 w-4" />
            New Session
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {connections.length === 0 && !isLoading && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
            Add a data connection first before starting an analysis session.
          </div>
        )}

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <MessageSquare className="h-10 w-10 text-muted-foreground/30" />
            <p className="mt-3 text-sm font-medium text-muted-foreground">No sessions yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Start a new session to begin analyzing data
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <Card
                key={session.id}
                className="cursor-pointer transition-all hover:shadow-md"
                onClick={() => router.push(`/sessions/${session.id}`)}
              >
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="rounded-md bg-aria-100 p-2">
                    <MessageSquare className="h-4 w-4 text-aria-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-semibold">{session.title}</p>
                    {session.session_summary && (
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {session.session_summary}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {session.key_findings.length > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {session.key_findings.length} findings
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatRelative(session.updated_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={showCreate} onOpenChange={(o) => !o && setShowCreate(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Analysis Session</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <Label>Session Title</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Q2 Revenue Analysis"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Data Connection</Label>
              <Select value={connectionId} onValueChange={setConnectionId} required>
                <SelectTrigger>
                  <SelectValue placeholder="Select a connection" />
                </SelectTrigger>
                <SelectContent>
                  {connections.map((c) => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={creating || !title || !connectionId}>
                Start Session
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
