"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Loader2, CheckCircle, XCircle, Bell, X, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

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
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [dismissedIds, setDismissedIds] = useState<string[]>(loadDismissed);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Persist dismissed IDs
  useEffect(() => {
    saveDismissed(dismissedIds);
  }, [dismissedIds]);

  // Poll for process updates
  useEffect(() => {
    const fetchProcesses = async () => {
      try {
        const res = await fetch("/api/task/processes");
        if (res.ok) {
          const data: ProcessInfo[] = await res.json();
          setProcesses(data.filter((p) => !dismissedIds.includes(p.id)));
        }
      } catch {
        // Silently fail
      }
    };
    fetchProcesses();
    const interval = setInterval(fetchProcesses, 2000);
    return () => clearInterval(interval);
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

  const handleDismiss = useCallback((pid: string) => {
    setDismissedIds((prev) => [...prev, pid]);
  }, []);

  const handleClearAll = useCallback(() => {
    setDismissedIds((prev) => [...prev, ...processes.map((p) => p.id)]);
  }, [processes]);

  const activeCount = processes.filter((p) => p.status === "running").length;
  const completedCount = processes.filter((p) => p.status === "completed").length;
  const totalCount = processes.length;

  // Shared process list renderer
  const renderProcessList = () => (
    <div className={`${embedded ? 'max-h-[200px]' : 'max-h-[360px]'} overflow-y-auto p-2 space-y-1.5`}>
      {processes.length === 0 ? (
        <div className="text-center py-6 text-slate-600 text-xs italic">
          No active tasks in registry
        </div>
      ) : (
        processes.map((process) => (
          <div
            key={process.id}
            className={`
              relative flex items-start gap-3 p-2.5 rounded-lg border transition-all
              ${
                process.status === "running"
                  ? "bg-sky-500/5 border-sky-500/20"
                  : process.status === "completed"
                  ? "bg-emerald-500/5 border-emerald-500/15"
                  : "bg-rose-500/5 border-rose-500/15"
              }
            `}
          >
            {/* Status Icon */}
            <div className="shrink-0 mt-0.5">
              {process.status === "running" && (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
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
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-slate-200 truncate pr-2">
                  {process.name}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDismiss(process.id);
                  }}
                  className="text-slate-600 hover:text-white transition-colors shrink-0"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>

              <div className="text-[10px] text-slate-500 mt-0.5 truncate font-mono">
                {process.message || (process.status === "running" ? "Processing..." : process.status)}
              </div>

              {process.status === "running" && process.progress && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-grow h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full"
                      initial={{ width: "0%" }}
                      animate={{ width: getProgressPercent(process.progress) }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-[9px] text-slate-500 font-mono font-bold shrink-0">
                    {process.progress}
                  </span>
                </div>
              )}

              <div className="flex items-center gap-2 mt-1.5 opacity-50">
                 {process.end_time ? (
                  <span className="text-[9px] font-mono text-slate-500">
                    {formatRelativeTime(process.end_time)}
                  </span>
                ) : (
                  <span className="text-[9px] font-mono text-slate-500 flex items-center gap-1.5">
                    <div className="w-1 h-1 rounded-full bg-sky-500 animate-pulse" />
                    Started {formatRelativeTime(process.start_time)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))
      )}
      {processes.length > 0 && (
        <button
          onClick={handleClearAll}
          className="w-full text-center text-[10px] font-bold text-slate-500 hover:text-rose-400 py-2 transition-colors flex items-center justify-center gap-2 border-t border-white/5 mt-2 pt-3"
        >
          <Trash2 className="w-3 h-3" /> CLEAR COMPLETED TASKS
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
          flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-all h-8
          ${isOpen 
            ? 'bg-white/10 border-white/20' 
            : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/15'
          }
        `}
        title="System Tasks & Processes"
      >
        <div className="relative">
          <Bell className={`w-4 h-4 ${activeCount > 0 ? 'text-sky-400 pulse-sky' : 'text-slate-400'}`} />
          {activeCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500" />
            </span>
          )}
        </div>
        
        {totalCount > 0 && (
          <div className="flex items-center gap-2 font-mono text-[10px] font-bold tracking-tighter">
            <div className="flex items-center gap-1">
              <span className="text-slate-500">R:</span>
              <span className={activeCount > 0 ? 'text-sky-400' : 'text-slate-600'}>{activeCount}</span>
            </div>
            <div className="w-px h-2.5 bg-white/10" />
            <div className="flex items-center gap-1">
              <span className="text-slate-500">D:</span>
              <span className={completedCount > 0 ? 'text-emerald-500' : 'text-slate-600'}>{completedCount}</span>
            </div>
          </div>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.1 }}
            className="absolute right-0 top-full mt-2 w-80 bg-[#0f172a] border border-slate-700/50 rounded-xl shadow-2xl backdrop-blur-3xl z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="p-3 border-b border-slate-700/50 flex justify-between items-center bg-slate-900/50">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Tasks {activeCount > 0 && <span className="text-sky-400 ml-1">({activeCount} running)</span>}
              </span>
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
