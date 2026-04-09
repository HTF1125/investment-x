'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Loader2, Search, Waves, X } from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
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

function levelBadge(level: string) {
  const l = level.toUpperCase();
  if (l === 'ERROR' || l === 'CRITICAL')
    return 'bg-destructive/[0.08] text-destructive border-destructive/20';
  if (l === 'WARNING')
    return 'bg-warning/[0.08] text-warning border-warning/20';
  return 'bg-primary/[0.06] text-primary border-primary/15';
}

export default function AdminLogViewer() {
  const { token } = useAuth();
  const { theme } = useTheme();
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

  // SSE stream
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

  const formStyle = { colorScheme: theme === 'light' ? 'light' as const : 'dark' as const, backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' };

  return (
    <div className="space-y-3">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        {/* Stats */}
        <div className="flex items-center gap-2">
          <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">{stats.total} loaded</span>
          {stats.errors > 0 && (
            <>
              <span className="w-px h-3 bg-border/30" />
              <span className="text-[11.5px] font-mono text-destructive/60 tabular-nums">{stats.errors} errors</span>
            </>
          )}
          {stats.warnings > 0 && (
            <>
              <span className="w-px h-3 bg-border/30" />
              <span className="text-[11.5px] font-mono text-warning/60 tabular-nums">{stats.warnings} warn</span>
            </>
          )}
          {stats.services > 0 && (
            <>
              <span className="w-px h-3 bg-border/30" />
              <span className="text-[11.5px] font-mono text-muted-foreground/40 tabular-nums">{stats.services} svc</span>
            </>
          )}
        </div>

        {/* Stream badge */}
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-[var(--radius)] border text-[11px] font-mono ${
          streamState === 'live'
            ? 'border-success/20 text-success/70'
            : streamState === 'error'
              ? 'border-destructive/20 text-destructive/70'
              : 'border-warning/20 text-warning/70'
        }`}>
          <Waves className="w-2.5 h-2.5" />
          {streamState === 'live' ? 'LIVE' : streamState === 'error' ? 'RECONNECTING' : 'CONNECTING'}
        </span>

        <div className="flex-1 min-w-[8px]" />

        {/* Search */}
        <div className="relative order-last sm:order-none w-full sm:w-auto">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/40" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search logs..."
            className="h-7 w-full sm:w-52 pl-7 pr-2.5 text-[12.5px] border border-border/40 rounded-[var(--radius)] bg-background text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
            style={formStyle}
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/30 hover:text-foreground">
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Level filter */}
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value as (typeof LEVELS)[number])}
          className="h-7 px-2 text-[12.5px] border border-border/40 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50 cursor-pointer"
          style={formStyle}
        >
          {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>

        {/* Limit */}
        <select
          value={String(limit)}
          onChange={(e) => setLimit(Number(e.target.value) as (typeof LIMITS)[number])}
          className="h-7 px-2 text-[12.5px] border border-border/40 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50 cursor-pointer"
          style={formStyle}
        >
          {LIMITS.map((l) => <option key={l} value={l}>Last {l}</option>)}
        </select>
      </div>

      {/* ── Log entries ── */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/30" />
        </div>
      ) : isError ? (
        <div className="flex items-center justify-center py-16">
          <span className="text-[12.5px] text-destructive flex items-center gap-1.5">
            <AlertTriangle className="w-3 h-3" />{(error as Error)?.message || 'Failed to load logs.'}
          </span>
        </div>
      ) : logs.length === 0 ? (
        <div className="py-16 text-center text-[12.5px] text-muted-foreground/30 font-mono">No logs matched the current filters.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/30">
                <th className="stat-label text-left px-3 py-2 w-16">Level</th>
                <th className="stat-label text-left px-3 py-2 w-36">Time</th>
                <th className="stat-label text-left px-3 py-2 w-28">Logger</th>
                <th className="stat-label text-left px-3 py-2">Message</th>
                <th className="stat-label text-right px-3 py-2 w-32 hidden lg:table-cell">Location</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-border/10 hover:bg-foreground/[0.02] transition-colors align-top">
                  <td className="px-3 py-2">
                    <span className={`inline-flex px-1.5 py-0.5 rounded-[calc(var(--radius)-2px)] border text-[11px] font-mono font-semibold ${levelBadge(log.level)}`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-[11.5px] font-mono text-muted-foreground/40 whitespace-nowrap tabular-nums">
                    {new Date(log.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-[11.5px] font-mono text-foreground/60 truncate max-w-[140px]">{log.logger_name}</div>
                    {log.service && (
                      <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground/30">{log.service}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <div className="text-[12.5px] text-foreground/80 whitespace-pre-wrap break-words max-w-xl">{log.message}</div>
                    {log.exception && (
                      <pre className="mt-1.5 p-2 rounded-[calc(var(--radius)-2px)] border border-destructive/15 bg-destructive/[0.04] text-[11.5px] font-mono leading-relaxed text-destructive/70 whitespace-pre-wrap overflow-x-auto max-h-40">
                        {log.exception}
                      </pre>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right hidden lg:table-cell">
                    {log.path && (
                      <span className="text-[11px] font-mono text-muted-foreground/25 break-all">
                        {log.path.split('/').pop()}{log.line_no ? `:${log.line_no}` : ''}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Refreshing */}
      {isFetching && !isLoading && (
        <div className="flex items-center gap-1.5 text-[11.5px] font-mono text-muted-foreground/30">
          <Loader2 className="w-3 h-3 animate-spin" />Refreshing...
        </div>
      )}
    </div>
  );
}
