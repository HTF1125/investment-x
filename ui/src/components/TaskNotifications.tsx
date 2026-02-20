"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2, CheckCircle, XCircle, X, Trash2, Activity, Play, Archive, List, ListChecks } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetchJson } from "@/lib/api";

interface ProcessInfo {
  id: string;
  name: string;
  status: "running" | "completed" | "failed";
  start_time: string;
  end_time?: string;
  message?: string;
  progress?: string;
}

export default function TaskNotifications({ embedded = false }: { embedded?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  // Push updates (SSE) for near-real-time task refresh
  useEffect(() => {
    const es = new EventSource('/api/task/stream');
    const refresh = () => queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    es.addEventListener('task', refresh as EventListener);
    es.addEventListener('ready', refresh as EventListener);
    es.onerror = () => {
      // Fallback polling still active; browser auto-reconnects SSE.
    };
    return () => {
      es.removeEventListener('task', refresh as EventListener);
      es.removeEventListener('ready', refresh as EventListener);
      es.close();
    };
  }, [queryClient]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Use React Query for polling
  const { data: allProcesses = [] } = useQuery({
    queryKey: ['task-processes'],
    queryFn: () => apiFetchJson<ProcessInfo[]>("/api/task/processes"),
    enabled: true,
    refetchInterval: (query) => {
      const data = (query.state.data as ProcessInfo[] | undefined) ?? [];
      const hasRunning = data.some((p) => p.status === "running");
      if (hasRunning) return 700;
      if (embedded || isOpen) return 1500;
      return 5000;
    },
    refetchIntervalInBackground: false,
    staleTime: 3000,
  });

  const processes = allProcesses;

  const handleDismiss = async (pid: string) => {
    try {
      await apiFetchJson(`/api/task/process/${pid}/dismiss`, { method: 'POST' });
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    }
  };

  const handleClearAll = async () => {
    try {
      await apiFetchJson('/api/task/process/dismiss-completed', { method: 'POST' });
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    }
  };

  const activeCount = processes.filter((p) => p.status === "running").length;
  const completedCount = processes.filter((p) => p.status === "completed").length;
  const failedCount = processes.filter((p) => p.status === "failed").length;

  // Shared process list renderer
  const renderProcessList = () => (
    <div className={`${embedded ? 'max-h-[260px]' : 'max-h-[330px]'} overflow-y-auto custom-scrollbar p-1.5 space-y-1.5`}>
      {processes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground opacity-60">
            <Activity className="w-6 h-6 mb-1.5 stroke-1" />
            <span className="text-[11px] font-medium">System Idle</span>
        </div>
      ) : (
        <AnimatePresence initial={false}>
            {processes.map((process) => (
            <motion.div
                key={process.id}
                layout
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className={`
                relative flex items-start gap-2.5 p-2.5 rounded-lg border backdrop-blur-sm transition-all group
                ${
                    process.status === "running"
                    ? "bg-sky-500/5 border-sky-500/20 shadow-[0_0_15px_-5px_rgba(14,165,233,0.15)]"
                    : process.status === "completed"
                    ? "bg-emerald-500/5 border-emerald-500/10"
                    : "bg-rose-500/5 border-rose-500/10"
                }
                `}
            >
                {/* Status Icon */}
                <div className="shrink-0 mt-0.5">
                {process.status === "running" && (
                    <div className="relative">
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
                        <div className="absolute inset-0 blur-sm bg-sky-400/30 rounded-full animate-pulse" />
                    </div>
                )}
                {process.status === "completed" && (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                )}
                {process.status === "failed" && (
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                )}
                </div>

                {/* Content */}
                <div className="flex-grow min-w-0">
                <div className="flex justify-between items-start gap-2">
                    <span className="text-[10px] font-medium text-foreground truncate leading-tight">
                    {process.name}
                    </span>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleDismiss(process.id);
                        }}
                        className="text-muted-foreground hover:text-foreground transition-colors shrink-0 opacity-0 group-hover:opacity-100 p-0.5 hover:bg-accent/10 rounded"
                    >
                        <X className="w-2.5 h-2.5" />
                    </button>
                </div>

                <div className="mt-0.5 flex items-center justify-between gap-2 text-[9px] font-mono text-muted-foreground/80">
                    <span className="truncate flex items-center gap-1">
                      {process.status === 'running' && <Play className="w-2 h-2 fill-current shrink-0" />}
                      <span className="truncate">{process.message || (process.status === "running" ? "Processing..." : process.status)}</span>
                    </span>
                    <span className="shrink-0">
                      {process.end_time
                        ? `${formatRelativeTime(process.end_time)} • ${formatDuration(process.start_time, process.end_time)}`
                        : `Started ${formatRelativeTime(process.start_time)}`}
                    </span>
                </div>

                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1 w-full bg-secondary rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full"
                      initial={{ width: "0%" }}
                      animate={{ width: getRowPercent(process) }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-[9px] font-mono text-sky-400 shrink-0">
                    {getRowPercent(process)}
                  </span>
                </div>
                </div>
            </motion.div>
            ))}
        </AnimatePresence>
      )}
      
      {(completedCount > 0 || failedCount > 0) && (
        <button
          onClick={handleClearAll}
          className="w-full group flex items-center justify-center gap-1.5 py-1.5 mt-1 text-[10px] font-semibold text-muted-foreground hover:text-foreground hover:bg-accent/10 rounded-md transition-all border border-transparent hover:border-border/50"
        >
          <Trash2 className="w-2.5 h-2.5 group-hover:text-rose-400 transition-colors" /> 
          CLEAR COMPLETED
        </button>
      )}
    </div>
  );

  // Embedded mode: just render the list inline
  if (embedded) {
    return renderProcessList();
  }

  // Standalone mode: bell button + dropdown
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center gap-2.5 px-2.5 py-1 rounded-lg border transition-all h-8 overflow-hidden group
          ${isOpen 
            ? 'bg-accent/20 border-accent/40 text-foreground shadow-lg shadow-sky-500/10' 
            : 'bg-secondary/20 border-border/50 text-muted-foreground hover:bg-accent/10 hover:border-border hover:text-foreground shadow-sm'
          }
        `}
        title="System Tasks & Processes"
      >
        <div className="relative w-4 h-4 flex items-center justify-center">
          {activeCount > 0 && (
            <span className="absolute inset-0 rounded-full border border-sky-400/40 animate-spin" />
          )}
          <ListChecks className={`w-3.5 h-3.5 ${activeCount > 0 ? 'text-sky-400' : 'text-current'}`} />
        </div>
        
        {processes.length > 0 && (
            <div className="hidden sm:flex items-center gap-2.5 font-mono text-[10px] font-bold border-l border-border pl-2.5">
                {activeCount > 0 && (
                    <span className="text-sky-400 flex items-center gap-1">
                        {activeCount}
                        <Loader2 className="w-2.5 h-2.5 animate-spin" />
                    </span>
                )}
                {completedCount > 0 && (
                    <span className="text-emerald-500">{completedCount}</span>
                )}
                {failedCount > 0 && (
                    <span className="text-rose-500">{failedCount}</span>
                )}
            </div>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute right-0 top-full mt-2 w-72 sm:w-80 bg-background/95 border border-border rounded-xl shadow-2xl backdrop-blur-2xl z-50 overflow-hidden ring-1 ring-border/50"
          >
            {/* Header */}
            <div className="px-3 py-2 border-b border-border flex justify-between items-center bg-accent/5">
              <div className="flex items-center gap-2">
                <List className="w-3 h-3 text-muted-foreground" />
                <span className="text-[11px] font-semibold text-foreground uppercase tracking-wider">
                    Task Manager
                </span>
              </div>
              <div className="flex gap-2">
                  <span className="text-[10px] font-mono text-muted-foreground bg-accent/10 px-1.5 py-0.5 rounded">
                    {activeCount} Active
                  </span>
              </div>
            </div>

            {renderProcessList()}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Parse progress string like "2/4" into a CSS percentage. */
function getProgressPercent(progress: string): string {
  const value = (progress || "").trim();
  if (!value) return "0%";

  // Already in percent format
  if (value.endsWith("%")) {
    const pct = parseInt(value.replace("%", ""), 10);
    if (isNaN(pct)) return "0%";
    return `${Math.max(0, Math.min(100, pct))}%`;
  }

  // Fraction format: "current/total"
  const parts = value.split("/");
  if (parts.length !== 2) return "0%";
  const current = parseInt(parts[0], 10);
  const total = parseInt(parts[1], 10);
  if (isNaN(current) || isNaN(total) || total === 0) return "0%";
  return `${Math.max(0, Math.min(100, Math.round((current / total) * 100)))}%`;
}

function getRowPercent(process: ProcessInfo): string {
  if (process.status === "completed") return "100%";
  if (process.status === "failed") {
    if (!process.progress) return "0%";
    return getProgressPercent(process.progress);
  }
  if (!process.progress) return "0%";
  return getProgressPercent(process.progress);
}

function formatDuration(startIso: string, endIso: string): string {
  try {
    const start = new Date(startIso).getTime();
    const end = new Date(endIso).getTime();
    const sec = Math.max(0, Math.floor((end - start) / 1000));
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    const rem = sec % 60;
    if (min < 60) return rem ? `${min}m ${rem}s` : `${min}m`;
    const hr = Math.floor(min / 60);
    const minRem = min % 60;
    return minRem ? `${hr}h ${minRem}m` : `${hr}h`;
  } catch {
    return "-";
  }
}

/** Format ISO timestamp into a human-readable relative time. */
function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 10) return "just now";
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return date.toLocaleDateString();
  } catch {
    return isoString;
  }
}
