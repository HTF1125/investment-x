'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, AlertTriangle, Loader2, Search, ShieldAlert, Waves } from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { apiFetchJson } from '@/lib/api';

type LogEntry = {
  id: string;
  level: string;
  logger_name: string;
  module?: string | null;
  function?: string | null;
  message: string;
  path?: string | null;
  line_no?: number | null;
  service?: string | null;
  exception?: string | null;
  created_at: string;
};

const LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const;
const LIMITS = [100, 200, 500] as const;

function levelTone(level: string) {
  const normalized = level.toUpperCase();
  if (normalized === 'ERROR' || normalized === 'CRITICAL') {
    return 'border-rose-500/30 bg-rose-500/10 text-rose-300';
  }
  if (normalized === 'WARNING') {
    return 'border-amber-500/30 bg-amber-500/10 text-amber-300';
  }
  return 'border-primary/30 bg-primary/10 text-primary';
}

export default function AdminLogViewer() {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [level, setLevel] = useState<(typeof LEVELS)[number]>('ALL');
  const [limit, setLimit] = useState<(typeof LIMITS)[number]>(200);
  const [streamState, setStreamState] = useState<'connecting' | 'live' | 'error'>('connecting');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => clearTimeout(timer);
  }, [search]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (level !== 'ALL') params.set('level', level);
    if (debouncedSearch) params.set('search', debouncedSearch);
    return params.toString();
  }, [debouncedSearch, level, limit]);

  const { data: logs = [], isLoading, isFetching, isError, error } = useQuery<LogEntry[]>({
    queryKey: ['admin-logs', level, debouncedSearch, limit],
    queryFn: () => apiFetchJson<LogEntry[]>(`/api/admin/logs?${queryString}`),
    staleTime: 15_000,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const params = new URLSearchParams();
    if (level !== 'ALL') params.set('level', level);
    if (debouncedSearch) params.set('search', debouncedSearch);
    if (token) params.set('token', token);

    const url = `/api/admin/logs/stream?${params.toString()}`;
    const stream = new EventSource(url);

    setStreamState('connecting');

    stream.addEventListener('ready', () => setStreamState('live'));
    stream.addEventListener('log', () => {
      setStreamState('live');
      queryClient.invalidateQueries({ queryKey: ['admin-logs'] });
    });
    stream.addEventListener('error', () => setStreamState('error'));
    stream.onerror = () => setStreamState('error');

    return () => stream.close();
  }, [debouncedSearch, level, queryClient, token]);

  const stats = useMemo(() => {
    const total = logs.length;
    const errors = logs.filter((log) => ['ERROR', 'CRITICAL'].includes((log.level || '').toUpperCase())).length;
    const warnings = logs.filter((log) => (log.level || '').toUpperCase() === 'WARNING').length;
    const services = new Set(logs.map((log) => log.service).filter(Boolean)).size;
    return { total, errors, warnings, services };
  }, [logs]);

  return (
    <div className="space-y-6">
      <div className="rounded-[var(--radius)] border border-border/50 bg-card p-6 md:p-8 shadow-md">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center">
                <Activity className="w-5 h-5 text-primary" />
              </div>
              Runtime Logs
            </h2>
            <p className="text-xs text-muted-foreground font-mono tracking-wider uppercase mt-1">
              Database-backed live application logging
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[11px] font-semibold ${
                streamState === 'live'
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                  : streamState === 'error'
                    ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
              }`}
            >
              <Waves className="w-3.5 h-3.5" />
              {streamState === 'live' ? 'Live stream active' : streamState === 'error' ? 'Stream reconnecting' : 'Connecting stream'}
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/50 text-[11px] text-muted-foreground">
              <ShieldAlert className="w-3.5 h-3.5 text-primary" />
              Admin only
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-6">
          <StatCard label="Loaded" value={String(stats.total)} tone="neutral" />
          <StatCard label="Errors" value={String(stats.errors)} tone="rose" />
          <StatCard label="Warnings" value={String(stats.warnings)} tone="amber" />
          <StatCard label="Services" value={String(stats.services)} tone="sky" />
        </div>
      </div>

      <div className="rounded-[var(--radius)] border border-border/50 bg-card p-6 md:p-8 shadow-md">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <label className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search logger, module, service, or message..."
              className="w-full pl-11 pr-4 py-3 rounded-lg bg-background border border-border text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </label>

          <select
            value={level}
            onChange={(event) => setLevel(event.target.value as (typeof LEVELS)[number])}
            className="px-4 py-3 rounded-lg bg-background border border-border text-sm text-foreground outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/20 transition-all"
          >
            {LEVELS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

          <select
            value={String(limit)}
            onChange={(event) => setLimit(Number(event.target.value) as (typeof LIMITS)[number])}
            className="px-4 py-3 rounded-lg bg-background border border-border text-sm text-foreground outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/20 transition-all"
          >
            {LIMITS.map((item) => (
              <option key={item} value={item}>
                Last {item}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="py-20 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">Loading runtime logs...</p>
          </div>
        ) : isError ? (
          <div className="py-20 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-sm text-rose-300">
              <AlertTriangle className="w-4 h-4" />
              {(error as Error)?.message || 'Failed to load runtime logs.'}
            </div>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-20 text-center text-sm text-muted-foreground">
            No logs matched the current filters.
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            {logs.map((log) => (
              <div key={log.id} className="rounded-md border border-border/50 bg-background/40 px-4 py-3 backdrop-blur-sm">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-semibold ${levelTone(log.level)}`}>
                      {log.level}
                    </span>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {new Date(log.created_at).toLocaleString()}
                    </span>
                    <span className="text-[11px] text-foreground font-medium">
                      {log.logger_name}
                    </span>
                    {log.module && (
                      <span className="text-[11px] text-muted-foreground font-mono">
                        {log.module}
                        {log.function ? `.${log.function}` : ''}
                      </span>
                    )}
                    {log.service && (
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
                        {log.service}
                      </span>
                    )}
                  </div>
                  {log.path && (
                    <span className="text-[10px] text-muted-foreground font-mono break-all">
                      {log.path}{log.line_no ? `:${log.line_no}` : ''}
                    </span>
                  )}
                </div>

                <div className="mt-2 text-sm text-foreground whitespace-pre-wrap break-words">
                  {log.message}
                </div>

                {log.exception && (
                  <pre className="mt-3 overflow-x-auto rounded-lg border border-rose-500/20 bg-rose-500/8 p-3 text-[11px] leading-relaxed text-rose-200 whitespace-pre-wrap">
                    {log.exception}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}

        {isFetching && !isLoading && (
          <div className="mt-3 text-[11px] text-muted-foreground font-mono flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" />
            Refreshing log view...
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: 'neutral' | 'rose' | 'amber' | 'sky';
}) {
  const toneClass =
    tone === 'rose'
      ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
      : tone === 'amber'
        ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
        : tone === 'sky'
          ? 'border-primary/30 bg-primary/10 text-primary'
          : 'border-border/50 bg-background/40 text-foreground';

  return (
    <div className={`rounded-lg border px-4 py-3 ${toneClass}`}>
      <div className="text-[10px] font-mono uppercase tracking-wider opacity-70 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
