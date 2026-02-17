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

export default function TaskNotifications() {
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
  const badgeCount = processes.length;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors relative"
        title="Tasks & Notifications"
      >
        <Bell className="w-5 h-5" />
        {badgeCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2.5 w-2.5">
            {activeCount > 0 ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500" />
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-500" />
            )}
          </span>
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
              {processes.length > 0 && (
                <button
                  onClick={handleClearAll}
                  className="text-[10px] text-slate-500 hover:text-rose-400 flex items-center gap-1 transition-colors"
                >
                  <Trash2 className="w-3 h-3" /> Clear All
                </button>
              )}
            </div>

            {/* Process List */}
            <div className="max-h-[360px] overflow-y-auto p-2 space-y-1.5 bg-slate-900/40">
              {processes.length === 0 ? (
                <div className="text-center py-8 text-slate-600 text-xs italic">
                  No tasks
                </div>
              ) : (
                processes.map((process) => (
                  <div
                    key={process.id}
                    className={`
                      relative flex items-start gap-3 p-3 rounded-lg border transition-all
                      ${
                        process.status === "running"
                          ? "bg-slate-800/50 border-sky-500/20"
                          : process.status === "completed"
                          ? "bg-emerald-900/10 border-emerald-500/15"
                          : "bg-rose-900/10 border-rose-500/15"
                      }
                    `}
                  >
                    {/* Status Icon */}
                    <div className="shrink-0 mt-0.5">
                      {process.status === "running" && (
                        <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
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
                      <div className="flex justify-between items-start">
                        <span className="text-sm font-medium text-slate-200 truncate pr-2">
                          {process.name}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDismiss(process.id);
                          }}
                          className="text-slate-600 hover:text-white transition-colors shrink-0"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Message + Progress */}
                      <div className="text-xs text-slate-500 mt-1 truncate">
                        {process.message || (process.status === "running" ? "Processing..." : process.status)}
                      </div>

                      {/* Progress bar for running tasks */}
                      {process.status === "running" && process.progress && (
                        <div className="mt-2 flex items-center gap-2">
                          <div className="flex-grow h-1 bg-slate-700/50 rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-gradient-to-r from-sky-500 to-indigo-500 rounded-full"
                              initial={{ width: "0%" }}
                              animate={{ width: getProgressPercent(process.progress) }}
                              transition={{ duration: 0.5, ease: "easeOut" }}
                            />
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono shrink-0">
                            {process.progress}
                          </span>
                        </div>
                      )}

                      {/* Timestamp */}
                      {process.end_time && (
                        <div className="text-[10px] text-slate-600 mt-1.5">
                          {formatRelativeTime(process.end_time)}
                        </div>
                      )}
                      {process.status === "running" && (
                        <div className="text-[10px] text-slate-700 mt-1">
                          Started {formatRelativeTime(process.start_time)}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
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
