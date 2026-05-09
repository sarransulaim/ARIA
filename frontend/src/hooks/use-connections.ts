"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { connectionsApi } from "@/lib/api/connections";
import { useConnectionStore } from "@/lib/store/connection-store";

export function useConnections() {
  const { connections, setConnections } = useConnectionStore();

  const query = useQuery({
    queryKey: ["connections"],
    queryFn: connectionsApi.list,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (query.data) setConnections(query.data);
  }, [query.data, setConnections]);

  return {
    connections,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
