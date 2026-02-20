"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2, CheckCircle, XCircle, Bell, X, Trash2, Activity, Play, Archive, List } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
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

const STORAGE_KEY = "ix-dismissed-tasks";

function loadDismissed(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveDismissed(ids: string[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids.slice(-200)));
  } catch {
    // Silently ignore
  }
}

export default function TaskNotifications({ embedded = false }: { embedded?: boolean }) {
  const [isOpen, setIsOpen] = useState(false);
  const [dismissedIds, setDismissedIds] = useState<string[]>(loadDismissed);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Persist dismissed IDs
  useEffect(() => {
    saveDismissed(dismissedIds);
  }, [dismissedIds]);

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
    refetchInterval: 2000, // Poll every 2s
    staleTime: 1000,
  });

  // Filter out dismissed tasks
  const processes = allProcesses.filter((p) => !dismissedIds.includes(p.id));

  const handleDismiss = (pid: string) => {
    setDismissedIds((prev) => [...prev, pid]);
  };

  const handleClearAll = () => {
    const completedOrFailed = processes
      .filter(p => p.status !== 'running')
      .map(p => p.id);
    setDismissedIds((prev) => [...prev, ...completedOrFailed]);
  };

  const activeCount = processes.filter((p) => p.status === "running").length;
  const completedCount = processes.filter((p) => p.status === "completed").length;
  const failedCount = processes.filter((p) => p.status === "failed").length;

  // Shared process list renderer
  const renderProcessList = () => (
    <div className={`${embedded ? 'max-h-[300px]' : 'max-h-[400px]'} overflow-y-auto custom-scrollbar p-2 space-y-2`}>
      {processes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground opacity-60">
            <Activity className="w-8 h-8 mb-2 stroke-1" />
            <span className="text-xs font-medium">System Idle</span>
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
                relative flex items-start gap-3 p-3 rounded-xl border backdrop-blur-sm transition-all group
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
                        <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                        <div className="absolute inset-0 blur-sm bg-sky-400/30 rounded-full animate-pulse" />
                    </div>
                )}
                {process.status === "completed" && (
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                )}
                {process.status === "failed" && (
                    <XCircle className="w-4 h-4 text-rose-400" />
                )}
                </div>

                {/* Content */}
                <div className="flex-grow min-w-0">
                <div className="flex justify-between items-start gap-2">
                    <span className="text-xs font-bold text-foreground truncate leading-tight">
                    {process.name}
                    </span>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            handleDismiss(process.id);
                        }}
                        className="text-muted-foreground hover:text-foreground transition-colors shrink-0 opacity-0 group-hover:opacity-100 p-0.5 hover:bg-accent/10 rounded"
                    >
                        <X className="w-3 h-3" />
                    </button>
                </div>

                <div className="text-[10px] text-muted-foreground mt-1 truncate font-mono flex items-center gap-1.5">
                    {process.status === 'running' && <Play className="w-2 h-2 fill-current" />}
                    {process.message || (process.status === "running" ? "Processing..." : process.status)}
                </div>

                {process.status === "running" && process.progress && (
                    <div className="mt-2.5">
                        <div className="flex justify-between text-[9px] text-muted-foreground font-mono mb-1">
                            <span>Progress</span>
                            <span className="text-sky-400 font-bold">{process.progress}</span>
                        </div>
                        <div className="h-1 bg-secondary rounded-full overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full shadow-[0_0_10px_rgba(14,165,233,0.5)]"
                                initial={{ width: "0%" }}
                                animate={{ width: getProgressPercent(process.progress) }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                            />
                        </div>
                    </div>
                )}

                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50 opacity-50">
                    {process.end_time ? (
                    <span className="text-[9px] font-mono text-muted-foreground">
                        Completed {formatRelativeTime(process.end_time)}
                    </span>
                    ) : (
                    <span className="text-[9px] font-mono text-muted-foreground flex items-center gap-1.5">
                        <div className="w-1 h-1 rounded-full bg-sky-500 animate-pulse" />
                        Started {formatRelativeTime(process.start_time)}
                    </span>
                    )}
                </div>
                </div>
            </motion.div>
            ))}
        </AnimatePresence>
      )}
      
      {(completedCount > 0 || failedCount > 0) && (
        <button
          onClick={handleClearAll}
          className="w-full group flex items-center justify-center gap-2 py-2 mt-2 text-[10px] font-bold text-muted-foreground hover:text-foreground hover:bg-accent/10 rounded-lg transition-all border border-transparent hover:border-border/50"
        >
          <Trash2 className="w-3 h-3 group-hover:text-rose-400 transition-colors" /> 
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
          flex items-center gap-3 px-3 py-1.5 rounded-xl border transition-all h-9 overflow-hidden group
          ${isOpen 
            ? 'bg-accent/20 border-accent/40 text-foreground shadow-lg shadow-sky-500/10' 
            : 'bg-secondary/20 border-border/50 text-muted-foreground hover:bg-accent/10 hover:border-border hover:text-foreground shadow-sm'
          }
        `}
        title="System Tasks & Processes"
      >
        <div className="relative">
          <Bell className={`w-3.5 h-3.5 ${activeCount > 0 ? 'text-sky-400' : 'text-current'}`} />
          {activeCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500" />
            </span>
          )}
        </div>
        
        {processes.length > 0 && (
            <div className="flex items-center gap-3 font-mono text-[10px] font-bold border-l border-border pl-3">
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
            className="absolute right-0 top-full mt-3 w-80 sm:w-96 bg-background/95 border border-border rounded-2xl shadow-2xl backdrop-blur-2xl z-50 overflow-hidden ring-1 ring-border/50"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-border flex justify-between items-center bg-accent/5">
              <div className="flex items-center gap-2">
                <List className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs font-bold text-foreground uppercase tracking-wider">
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
  const parts = progress.split("/");
  if (parts.length !== 2) return "50%";
  const current = parseInt(parts[0], 10);
  const total = parseInt(parts[1], 10);
  if (isNaN(current) || isNaN(total) || total === 0) return "50%";
  return `${Math.round((current / total) * 100)}%`;
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
