'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTheme } from '@/context/ThemeContext';
import { applyChartTheme } from '@/lib/chartTheme';
import { apiFetchJson } from '@/lib/api';
import { Activity, TrendingDown, TrendingUp, BarChart3, Zap, AlertTriangle, Loader2 } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Target { name: string; ticker: string; region: string; }

interface StressEvent {
  date: string;
  cause: string;
  causeKo: string;
  initialReturn: number;
  returns: Record<string, number | null>;
  isCurrent?: boolean;
  highlight?: 'danger' | 'warn';
}

interface IndexStressData {
  label: string;
  source: string;
  sourceDate: string;
  cbEvents: StressEvent[];
  cbHorizons: string[];
  cbAvg: Record<string, number>;
  crashEvents: StressEvent[];
  crashHorizons: string[];
  crashAvg: Record<string, number>;
  recoveryCurves: Record<string, { x: number[]; y: number[] }>;
  insights: { positive: string[]; caution: string[] };
  valuation: string[];
  currentEvent?: { date: string; drop: number; dropLabel: string } | null;
}

type ViewMode = 'cb' | 'crash' | 'recovery';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (v: number | null | undefined, suffix = '%') => {
  if (v === null || v === undefined) return '—';
  const s = v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1);
  return `${s}${suffix}`;
};

const cellColor = (v: number | null | undefined) => {
  if (v === null || v === undefined) return 'text-muted-foreground/40';
  if (v > 0) return 'text-emerald-500';
  if (v < 0) return 'text-red-500';
  return 'text-muted-foreground';
};

const bgBar = (v: number | null | undefined, max: number) => {
  if (v === null || v === undefined) return {};
  const pct = Math.min(Math.abs(v) / max * 100, 100);
  const color = v >= 0 ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)';
  return { background: `linear-gradient(90deg, ${color} ${pct}%, transparent ${pct}%)` };
};

// ─── Recovery Chart Component ─────────────────────────────────────────────────

function RecoveryChart({ data, selectedEvents, theme }: {
  data: IndexStressData;
  selectedEvents: string[];
  theme: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const plotlyRef = useRef<any>(null);

  const render = useCallback(() => {
    if (!plotlyRef.current || !ref.current) return;

    const colors = ['#38bdf8', '#f97316', '#a78bfa', '#34d399', '#f472b6', '#facc15', '#fb923c', '#60a5fa'];
    const curves = data.recoveryCurves;
    const allDates = Object.keys(curves);
    const active = selectedEvents.length > 0 ? selectedEvents : allDates;

    const traces = active.map((date, i) => {
      const curve = curves[date];
      if (!curve) return null;
      const ev = data.cbEvents.find(e => e.date === date);
      const isCurrent = ev?.isCurrent;
      return {
        x: curve.x, y: curve.y, type: 'scatter' as const, mode: 'lines' as const,
        name: `${date.slice(0, 4)} ${ev?.cause || ''}`,
        line: { color: isCurrent ? '#ef4444' : colors[i % colors.length], width: isCurrent ? 3 : 1.5 },
      };
    }).filter(Boolean);

    // Average line (excl. current)
    const refDates = allDates.filter(d => !data.cbEvents.find(e => e.date === d)?.isCurrent);
    if (refDates.length > 0) {
      const refX = curves[refDates[0]]?.x ?? [];
      const avgY = refX.map(xVal => {
        const vals = refDates.map(d => { const c = curves[d]; if (!c) return null; const idx = c.x.indexOf(xVal); return idx >= 0 ? c.y[idx] : null; }).filter((v): v is number => v !== null);
        return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
      });
      traces.push({ x: refX, y: avgY as any, type: 'scatter', mode: 'lines', name: 'Average', line: { color: '#94a3b8', width: 2.5, dash: 'dash' as any } } as any);
    }

    const fig = {
      data: traces,
      layout: {
        title: { text: `${data.label} Recovery Paths After Crash (T0=100)`, font: { size: 13 } },
        xaxis: { title: { text: 'Trading Days from Event', font: { size: 11 } }, zeroline: true, zerolinecolor: 'rgba(148,163,184,0.3)', zerolinewidth: 2, gridcolor: 'rgba(148,163,184,0.08)' },
        yaxis: { title: { text: 'Rebased (T0=100)', font: { size: 11 } }, gridcolor: 'rgba(148,163,184,0.08)' },
        showlegend: true, legend: { orientation: 'h' as const, y: -0.2, font: { size: 10 } },
        margin: { t: 40, r: 20, b: 60, l: 50 }, hovermode: 'x unified' as const,
        shapes: [{ type: 'line' as const, x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper' as const, line: { color: 'rgba(239,68,68,0.4)', width: 1, dash: 'dot' as const } }],
      },
    };
    applyChartTheme(fig, theme as 'light' | 'dark', { transparentBackground: true });
    plotlyRef.current.react(ref.current, fig.data, fig.layout, { responsive: true, displayModeBar: false });
  }, [selectedEvents, theme, data]);

  useEffect(() => {
    let cancelled = false;
    import('plotly.js-dist-min').then(mod => { if (!cancelled) { plotlyRef.current = mod.default; render(); } });
    return () => { cancelled = true; };
  }, [render]);

  useEffect(() => { render(); }, [render]);
  return <div ref={ref} className="w-full h-[380px]" />;
}

// ─── Return Heatmap ───────────────────────────────────────────────────────────

function ReturnHeatmap({ events, horizons, theme, title }: {
  events: StressEvent[];
  horizons: string[];
  theme: string;
  title: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const plotlyRef = useRef<any>(null);

  const render = useCallback(() => {
    if (!plotlyRef.current || !ref.current) return;
    const labels = events.map(e => `${e.date.slice(2)} ${e.cause}`);
    const z = events.map(e => horizons.map(h => e.returns[h] ?? NaN));

    const fig = {
      data: [{
        type: 'heatmap' as const, z, x: horizons, y: labels,
        colorscale: [[0,'#ef4444'],[0.3,'#fca5a5'],[0.45,'#fef3c7'],[0.5,'#f5f5f4'],[0.55,'#d1fae5'],[0.7,'#6ee7b7'],[1,'#10b981']],
        zmid: 0, zmin: -25, zmax: 60,
        text: z.map(row => row.map(v => isNaN(v) ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`)),
        texttemplate: '%{text}', textfont: { size: 9 },
        hovertemplate: '%{y}<br>%{x}: %{text}<extra></extra>',
        showscale: true, colorbar: { title: { text: 'Return %', font: { size: 10 } }, thickness: 12, len: 0.5 },
      }],
      layout: {
        title: { text: title, font: { size: 13 } },
        xaxis: { title: { text: 'Horizon', font: { size: 11 } }, side: 'top' as const },
        yaxis: { autorange: 'reversed' as const, tickfont: { size: 9 } },
        margin: { t: 60, r: 80, b: 30, l: 180 },
        height: Math.max(300, events.length * 28 + 90),
      },
    };
    applyChartTheme(fig, theme as 'light' | 'dark', { transparentBackground: true });
    plotlyRef.current.react(ref.current, fig.data, fig.layout, { responsive: true, displayModeBar: false });
  }, [events, horizons, theme, title]);

  useEffect(() => {
    let cancelled = false;
    import('plotly.js-dist-min').then(mod => { if (!cancelled) { plotlyRef.current = mod.default; render(); } });
    return () => { cancelled = true; };
  }, [render]);

  useEffect(() => { render(); }, [render]);
  return <div ref={ref} className="w-full" />;
}

// ─── Stat Cards ───────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon }: { label: string; value: string; sub?: string; icon: React.ReactNode }) {
  return (
    <div className="panel-card p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-muted-foreground/50">{icon}</span>
        <span className="stat-label">{label}</span>
      </div>
      <div className="text-lg font-semibold font-mono text-foreground">{value}</div>
      {sub && <div className="text-[11.5px] text-muted-foreground/60 mt-0.5">{sub}</div>}
    </div>
  );
}

// ─── Stress Event Table ───────────────────────────────────────────────────────

function StressTable({ events, horizons, averages, returnLabel, onRowClick, selectedRows }: {
  events: StressEvent[];
  horizons: string[];
  averages: Record<string, number>;
  returnLabel: string;
  onRowClick?: (date: string) => void;
  selectedRows?: Set<string>;
}) {
  const maxReturn = useMemo(() => {
    let max = 0;
    for (const e of events) for (const v of Object.values(e.returns)) if (v !== null && v !== undefined) max = Math.max(max, Math.abs(v));
    return max || 1;
  }, [events]);

  const nonCurrentEvents = events.filter(e => !e.isCurrent);
  const avgInitial = nonCurrentEvents.length > 0 ? nonCurrentEvents.reduce((s, e) => s + e.initialReturn, 0) / nonCurrentEvents.length : 0;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12.5px] border-collapse">
        <thead>
          <tr className="border-b border-border/50">
            <th className="text-left px-3 py-2 text-muted-foreground/70 font-medium sticky left-0 bg-background z-10">Date</th>
            <th className="text-left px-3 py-2 text-muted-foreground/70 font-medium">Cause</th>
            <th className="text-right px-3 py-2 text-muted-foreground/70 font-medium whitespace-nowrap">{returnLabel}</th>
            {horizons.map(h => <th key={h} className="text-right px-3 py-2 text-muted-foreground/70 font-medium whitespace-nowrap">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {events.map((ev, idx) => {
            const isSelected = selectedRows?.has(ev.date);
            const rowBg = ev.isCurrent ? 'bg-red-500/[0.06]' : ev.highlight === 'warn' ? 'bg-amber-500/[0.04]' : isSelected ? 'bg-primary/[0.06]' : 'hover:bg-primary/[0.04]';
            const dateCls = ev.isCurrent ? 'text-red-500 font-semibold bg-red-500/[0.06]' : ev.highlight === 'warn' ? 'text-amber-500 bg-amber-500/[0.04]' : isSelected ? 'text-primary bg-primary/[0.06]' : 'text-foreground bg-background';
            const causeCls = ev.isCurrent ? 'text-red-500' : ev.highlight === 'warn' ? 'text-amber-500' : 'text-muted-foreground';
            return (
              <tr key={`${ev.date}-${idx}`} onClick={() => onRowClick?.(ev.date)}
                className={`border-b border-border/25 transition-colors ${onRowClick ? 'cursor-pointer' : ''} ${rowBg}`}>
                <td className={`px-3 py-1.5 font-mono whitespace-nowrap sticky left-0 z-10 ${dateCls}`}>{ev.date}</td>
                <td className={`px-3 py-1.5 ${causeCls}`}>{ev.cause}</td>
                <td className={`px-3 py-1.5 text-right font-mono ${cellColor(ev.initialReturn)}`} style={bgBar(ev.initialReturn, 20)}>{fmt(ev.initialReturn)}</td>
                {horizons.map(h => (
                  <td key={h} className={`px-3 py-1.5 text-right font-mono ${cellColor(ev.returns[h])}`} style={bgBar(ev.returns[h], maxReturn)}>{fmt(ev.returns[h])}</td>
                ))}
              </tr>
            );
          })}
          <tr className="border-t-2 border-border/50 bg-primary/[0.04]">
            <td className="px-3 py-1.5 font-mono font-semibold text-foreground sticky left-0 bg-primary/[0.04] z-10">Avg</td>
            <td className="px-3 py-1.5 text-muted-foreground font-medium">Excl. current</td>
            <td className="px-3 py-1.5 text-right font-mono font-semibold text-red-500">{fmt(avgInitial)}</td>
            {horizons.map(h => <td key={h} className={`px-3 py-1.5 text-right font-mono font-semibold ${cellColor(averages[h])}`}>{fmt(averages[h])}</td>)}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function StressTestContent({ embedded = false }: { embedded?: boolean }) {
  const { theme } = useTheme();
  const [view, setView] = useState<ViewMode>('cb');
  const [selectedCB, setSelectedCB] = useState<Set<string>>(new Set());
  const [selectedIndex, setSelectedIndex] = useState('KOSPI');

  const targetsQuery = useQuery({
    queryKey: ['macro-targets'],
    queryFn: () => apiFetchJson<{ targets: Target[] }>('/api/macro/targets'),
    staleTime: 300_000,
  });

  const stressQuery = useQuery({
    queryKey: ['stress-test', selectedIndex],
    queryFn: () => apiFetchJson<IndexStressData>(`/api/macro/stress-test?target=${encodeURIComponent(selectedIndex)}`),
    enabled: !!selectedIndex,
    staleTime: 600_000,
  });

  const toggleCB = (date: string) => {
    setSelectedCB(prev => { const next = new Set(prev); if (next.has(date)) next.delete(date); else next.add(date); return next; });
  };

  const data = stressQuery.data ?? null;

  const cbStats = useMemo(() => {
    if (!data?.cbEvents?.length) return null;
    const valid = data.cbEvents.filter(e => !e.isCurrent);
    if (!valid.length) return null;
    const avgDay = valid.reduce((s, e) => s + e.initialReturn, 0) / valid.length;
    const positiveT1 = valid.filter(e => (e.returns['+1T'] ?? 0) > 0).length;
    const t60Vals = valid.filter(e => e.returns['+60T'] != null);
    const avgT60 = t60Vals.length > 0 ? t60Vals.reduce((s, e) => s + (e.returns['+60T'] ?? 0), 0) / t60Vals.length : 0;
    return { avgDay, positiveT1, total: valid.length, avgT60 };
  }, [data]);

  return (
    <div className={`max-w-[1600px] mx-auto space-y-5 ${embedded ? 'px-3 py-4' : 'px-4 sm:px-6 py-5'}`}>
      {/* Header with index selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="page-title">Stress Test</h2>
            <p className="text-[12.5px] text-muted-foreground/60 mt-0.5">
              {data
                ? `Historical crash & recovery analysis — ${data.source} (${data.sourceDate})`
                : stressQuery.isLoading ? 'Computing stress test...' : 'Select an index'}
            </p>
          </div>
          <select
            value={selectedIndex}
            onChange={(e) => { setSelectedIndex(e.target.value); setSelectedCB(new Set()); }}
            className="border border-border/50 rounded-lg px-2.5 py-1 text-[12.5px] focus:outline-none focus:border-primary/40 text-foreground cursor-pointer"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          >
            {(targetsQuery.data?.targets ?? []).map(t => (
              <option key={t.name} value={t.name}>{t.name} — {t.region}</option>
            ))}
            {!targetsQuery.data && <option value="KOSPI">KOSPI — korea</option>}
          </select>
        </div>
        {data && (
          <div className="flex items-center gap-1">
            {([
              { id: 'cb' as ViewMode, label: 'Single-Day Crashes', icon: <Zap className="w-3 h-3" /> },
              { id: 'crash' as ViewMode, label: '2-Day Crashes', icon: <TrendingDown className="w-3 h-3" /> },
              { id: 'recovery' as ViewMode, label: 'Recovery Paths', icon: <TrendingUp className="w-3 h-3" /> },
            ]).map(t => (
              <button key={t.id} onClick={() => setView(t.id)}
                className={`h-7 px-2.5 rounded-md text-[12.5px] inline-flex items-center gap-1.5 border transition-colors ${
                  view === t.id ? 'border-border bg-primary/10 text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.06]'
                }`}>{t.icon}{t.label}</button>
            ))}
          </div>
        )}
      </div>

      {/* Loading state */}
      {stressQuery.isLoading && (
        <div className="panel-card p-12 flex flex-col items-center justify-center text-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-primary/40" />
          <p className="text-[12.5px] text-muted-foreground">Computing stress test for {selectedIndex}...</p>
        </div>
      )}

      {/* Error state */}
      {stressQuery.isError && !stressQuery.isLoading && (
        <div className="panel-card p-12 flex flex-col items-center justify-center text-center gap-3">
          <AlertTriangle className="w-8 h-8 text-muted-foreground/30" />
          <div>
            <p className="text-sm font-medium text-foreground">Failed to compute stress test for {selectedIndex}</p>
            <p className="text-[12.5px] text-muted-foreground/60 mt-1">
              {(stressQuery.error as any)?.message || 'Insufficient price data or computation error'}
            </p>
          </div>
        </div>
      )}

      {data && (
        <>
          {/* Summary stats */}
          {cbStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Avg Crash Day Return" value={fmt(cbStats.avgDay)} sub={`${cbStats.total} historical events`} icon={<Zap className="w-3.5 h-3.5" />} />
              <StatCard label="Next-Day Bounce Rate" value={`${cbStats.positiveT1}/${cbStats.total}`} sub={`${((cbStats.positiveT1 / cbStats.total) * 100).toFixed(0)}% positive +1T`} icon={<TrendingUp className="w-3.5 h-3.5" />} />
              <StatCard label="Avg +60T Return" value={fmt(cbStats.avgT60)} sub="After single-day crash" icon={<BarChart3 className="w-3.5 h-3.5" />} />
              {data.currentEvent && (
                <StatCard label={`${data.currentEvent.date}`} value={fmt(data.currentEvent.drop)} sub={data.currentEvent.dropLabel} icon={<Activity className="w-3.5 h-3.5" />} />
              )}
            </div>
          )}

          {/* Single-Day Crash View */}
          {view === 'cb' && (
            <div className="space-y-4">
              <div className="panel-card overflow-hidden">
                <div className="px-4 py-2.5 border-b border-border/40">
                  <h3 className="text-[13px] font-semibold text-foreground">{data.label} Single-Day Crash History — Forward Returns</h3>
                  <p className="text-[11.5px] text-muted-foreground/50 mt-0.5">Click rows to compare in recovery chart. {data.cbEvents.length} events detected.</p>
                </div>
                <StressTable events={data.cbEvents} horizons={data.cbHorizons} averages={data.cbAvg} returnLabel="Day Rtn" onRowClick={toggleCB} selectedRows={selectedCB} />
              </div>
              {data.cbEvents.length > 0 && (
                <div className="panel-card p-4">
                  <ReturnHeatmap events={data.cbEvents} horizons={data.cbHorizons} theme={theme} title={`${data.label} Single-Day Crash Forward Return Heatmap`} />
                </div>
              )}
            </div>
          )}

          {/* 2-Day Crash View */}
          {view === 'crash' && (
            <div className="space-y-4">
              <div className="panel-card overflow-hidden">
                <div className="px-4 py-2.5 border-b border-border/40">
                  <h3 className="text-[13px] font-semibold text-foreground">{data.label} 2-Day Crash History — Forward Returns</h3>
                  <p className="text-[11.5px] text-muted-foreground/50 mt-0.5">
                    Avg +40T: {fmt(data.crashAvg['+40T'])}, Avg +90T: {fmt(data.crashAvg['+90T'])}. {data.crashEvents.length} events detected.
                  </p>
                </div>
                <StressTable events={data.crashEvents} horizons={data.crashHorizons} averages={data.crashAvg} returnLabel="2D Rtn" />
              </div>
              {data.crashEvents.length > 0 && (
                <div className="panel-card p-4">
                  <ReturnHeatmap events={data.crashEvents} horizons={data.crashHorizons} theme={theme} title={`${data.label} 2-Day Crash Forward Return Heatmap`} />
                </div>
              )}
            </div>
          )}

          {/* Recovery Paths View */}
          {view === 'recovery' && (
            <div className="space-y-4">
              {Object.keys(data.recoveryCurves).length > 0 ? (
                <>
                  <div className="panel-card p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[12.5px] font-medium text-muted-foreground">Select events to compare:</span>
                      <button onClick={() => setSelectedCB(new Set())} className="text-[11.5px] text-primary hover:text-primary transition-colors">Show all</button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {data.cbEvents.filter(ev => data.recoveryCurves[ev.date]).map(ev => {
                        const active = selectedCB.has(ev.date);
                        return (
                          <button key={ev.date} onClick={() => toggleCB(ev.date)}
                            className={`h-6 px-2 rounded text-[11.5px] font-mono border transition-colors ${
                              active ? (ev.isCurrent ? 'border-red-500/50 bg-red-500/10 text-red-500' : 'border-primary/50 bg-primary/10 text-primary')
                                : 'border-border/40 text-muted-foreground/60 hover:text-foreground hover:border-border'
                            }`}>{ev.date.slice(0, 4)} {ev.cause}</button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="panel-card p-4">
                    <RecoveryChart data={data} selectedEvents={Array.from(selectedCB)} theme={theme} />
                  </div>
                </>
              ) : (
                <div className="panel-card p-8 text-center">
                  <p className="text-[12.5px] text-muted-foreground">No recovery curve data available for {data.label}</p>
                </div>
              )}

              {/* Insights */}
              {(data.insights.positive.length > 0 || data.insights.caution.length > 0 || data.valuation.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(data.insights.positive.length > 0 || data.insights.caution.length > 0) && (
                    <div className="panel-card p-4">
                      <h4 className="text-[13px] font-semibold text-foreground mb-2">Key Findings</h4>
                      <ul className="space-y-1.5 text-[12.5px] text-muted-foreground">
                        {data.insights.positive.map((t, i) => (
                          <li key={i} className="flex items-start gap-2"><span className="text-emerald-500 mt-0.5">+</span><span>{t}</span></li>
                        ))}
                        {data.insights.caution.map((t, i) => (
                          <li key={i} className="flex items-start gap-2"><span className="text-amber-500 mt-0.5">!</span><span>{t}</span></li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {data.valuation.length > 0 && (
                    <div className="panel-card p-4">
                      <h4 className="text-[13px] font-semibold text-foreground mb-2">Data Summary</h4>
                      <ul className="space-y-1.5 text-[12.5px] text-muted-foreground">
                        {data.valuation.map((t, i) => (
                          <li key={i} className="flex items-start gap-2"><span className="text-primary mt-0.5">&bull;</span><span>{t}</span></li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
