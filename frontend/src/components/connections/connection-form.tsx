"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { connectionsApi } from "@/lib/api/connections";
import { useConnectionStore } from "@/lib/store/connection-store";
import type { ConnectorType, ConnectionCreate } from "@/types";

interface ConnectionFormProps {
  open: boolean;
  onClose: () => void;
}

const DEFAULT_PORTS: Record<ConnectorType, string> = {
  postgresql: "5432",
  mysql: "3306",
  snowflake: "443",
  bigquery: "",
  csv: "",
};

export function ConnectionForm({ open, onClose }: ConnectionFormProps) {
  const upsertConnection = useConnectionStore((s) => s.upsertConnection);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [connectorType, setConnectorType] = useState<ConnectorType>("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("5432");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleConnectorChange = (value: ConnectorType) => {
    setConnectorType(value);
    setPort(DEFAULT_PORTS[value] ?? "");
  };

  const handleClose = () => {
    setName(""); setHost(""); setDatabase(""); setUsername(""); setPassword("");
    setError(null);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !host || !database) return;
    setIsLoading(true);
    setError(null);
    try {
      const payload: ConnectionCreate = {
        name,
        connector_type: connectorType,
        connection_config: { host, port: parseInt(port || "0"), database },
        credentials: { username, password },
        is_read_only: true,
      };
      const conn = await connectionsApi.create(payload);
      upsertConnection(conn);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create connection");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Data Connection</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Connection Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Production DB" required />
          </div>

          <div className="space-y-1.5">
            <Label>Database Type</Label>
            <Select value={connectorType} onValueChange={handleConnectorChange}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="postgresql">PostgreSQL</SelectItem>
                <SelectItem value="mysql">MySQL</SelectItem>
                <SelectItem value="snowflake">Snowflake</SelectItem>
                <SelectItem value="bigquery">BigQuery</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2 space-y-1.5">
              <Label>Host</Label>
              <Input value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" required />
            </div>
            <div className="space-y-1.5">
              <Label>Port</Label>
              <Input value={port} onChange={(e) => setPort(e.target.value)} placeholder="5432" />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Database</Label>
            <Input value={database} onChange={(e) => setDatabase(e.target.value)} placeholder="mydb" required />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1.5">
              <Label>Username</Label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="postgres" />
            </div>
            <div className="space-y-1.5">
              <Label>Password</Label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="••••••" />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>Cancel</Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Connect
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
