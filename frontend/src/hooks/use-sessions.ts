"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { sessionsApi } from "@/lib/api/sessions";
import { useSessionStore } from "@/lib/store/session-store";

export function useSessions() {
  const { sessions, setSessions } = useSessionStore();

  const query = useQuery({
    queryKey: ["sessions"],
    queryFn: sessionsApi.list,
    staleTime: 15_000,
  });

  useEffect(() => {
    if (query.data) setSessions(query.data);
  }, [query.data, setSessions]);

  return {
    sessions,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}
