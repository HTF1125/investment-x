"use client";

import React, { createContext, useContext, useEffect, useState, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

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

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const queryClient = useQueryClient();
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    let isConnected = false;

    const connectSSE = () => {
      es = new EventSource("/api/task/stream");

      es.addEventListener("ready", () => {
        isConnected = true;
        // On connect, fetch the initial state immediately to get true current status
        // of all ongoing tasks securely via React Query
        queryClient.invalidateQueries({ queryKey: ["task-processes"] });
      });

      es.addEventListener("task", (e) => {
        try {
          // You can parse e.data if the backend pushes the full updated list
          // But for strict state sync, invalidating the query and letting react-query handle
          // the single refetch is extremely stable.
          queryClient.invalidateQueries({ queryKey: ["task-processes"] });
        } catch (err) {
          console.error("Failed to parse SSE task event", err);
        }
      });

      es.onerror = () => {
          if (isConnected) {
              console.warn("SSE connection lost. Reconnecting...");
          }
          isConnected = false;
          es?.close();
          // Exponential backoff or simple fixed delay for reconnecting
          reconnectTimeoutRef.current = setTimeout(connectSSE, 3000);
      };
    };

    connectSSE();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (es) {
        es.close();
      }
    };
  }, [queryClient]);

  // Using contexts to just vend out the centralized cached react-query data 
  // without re-registering polling.
  const query = queryClient.getQueryData<ProcessInfo[]>(["task-processes"]);

  useEffect(() => {
      if (query) {
          setProcesses(query);
      }
  }, [query]);

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
