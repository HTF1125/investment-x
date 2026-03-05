"use client";

import React, { createContext, useContext, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { apiFetchJson } from "@/lib/api";

export interface ProcessInfo {
  id: string;
  name: string;
  status: "running" | "completed" | "failed";
  start_time: string;
  end_time?: string;
  message?: string;
  progress?: string;
}

interface TaskContextType {
  processes: ProcessInfo[];
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);
export const TASK_PROCESSES_QUERY_KEY = ["task-processes"] as const;
const INITIAL_RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_DELAY_MS = 30000;
const TASK_POLL_INTERVAL_MS = 30000;

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY_MS);
  const { isAuthenticated } = useAuth();

  const { data: processes = [] } = useQuery<ProcessInfo[]>({
    queryKey: TASK_PROCESSES_QUERY_KEY,
    queryFn: () => apiFetchJson<ProcessInfo[]>("/api/task/processes"),
    enabled: isAuthenticated,
    refetchInterval: isAuthenticated ? TASK_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: false,
    initialData: [],
  });

  useEffect(() => {
    if (isAuthenticated) {
      return;
    }

    reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    queryClient.removeQueries({ queryKey: TASK_PROCESSES_QUERY_KEY, exact: true });
  }, [isAuthenticated, queryClient]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let eventSource: EventSource | null = null;
    let disposed = false;

    const refreshProcesses = () =>
      queryClient.invalidateQueries({ queryKey: TASK_PROCESSES_QUERY_KEY });

    const scheduleReconnect = () => {
      if (disposed || reconnectTimeoutRef.current) {
        return;
      }

      const delay = reconnectDelayRef.current;
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectTimeoutRef.current = null;
        if (!disposed) {
          connectSSE();
        }
      }, delay);
      reconnectDelayRef.current = Math.min(
        reconnectDelayRef.current * 2,
        MAX_RECONNECT_DELAY_MS,
      );
    };

    const connectSSE = () => {
      if (disposed) {
        return;
      }

      let receivedReady = false;
      eventSource = new EventSource("/api/task/stream");

      eventSource.addEventListener("ready", () => {
        receivedReady = true;
        reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
        void refreshProcesses();
      });

      eventSource.addEventListener("task", () => {
        void refreshProcesses();
      });

      eventSource.onerror = () => {
        if (disposed) {
          return;
        }
        if (receivedReady) {
          console.warn("Task stream disconnected. Reconnecting...");
        }
        eventSource?.close();
        eventSource = null;
        scheduleReconnect();
      };
    };

    connectSSE();

    return () => {
      disposed = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [queryClient, isAuthenticated]);

  return (
    <TaskContext.Provider value={{ processes }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTasks() {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error("useTasks must be used within a TaskProvider");
  }
  return context;
}
