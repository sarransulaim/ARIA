"use client";
import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/layout/header";
import { Skeleton } from "@/components/ui/skeleton";
import { ConnectionCard } from "@/components/connections/connection-card";
import { ConnectionForm } from "@/components/connections/connection-form";
import { useConnections } from "@/hooks/use-connections";

export default function ConnectionsPage() {
  const { connections, isLoading } = useConnections();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Data Connections"
        description="Manage your database connections"
        actions={
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            Add Connection
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-32 rounded-lg" />)}
          </div>
        ) : connections.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="text-sm font-medium text-muted-foreground">No connections yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Add a database connection to start analyzing data
            </p>
            <Button className="mt-4" onClick={() => setShowForm(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Add your first connection
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connections.map((conn) => (
              <ConnectionCard key={conn.id} connection={conn} />
            ))}
          </div>
        )}
      </div>

      <ConnectionForm open={showForm} onClose={() => setShowForm(false)} />
    </div>
  );
}
