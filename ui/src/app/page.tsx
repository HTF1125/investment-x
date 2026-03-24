'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import dynamic from 'next/dynamic';
import AppShell from '@/components/layout/AppShell';
import Briefing from '@/components/intel/Briefing';
import MarketPulse from '@/components/dashboard/MarketPulse';
import { RefreshCw, Clock, Info, ChevronDown } from 'lucide-react';
import { type Period, PERIODS } from '@/components/dashboard/Technicals';
import { apiFetchJson } from '@/lib/api';
import { useQueryClient, useQuery } from '@tanstack/react-query';

const Technicals = dynamic(() => import('@/components/dashboard/Technicals'), {
  ssr: false,
  loading: () => (
    <div className="h-[300px] flex items-center justify-center">
      <div className="w-3.5 h-3.5 border-2 border-border/50 border-t-foreground/60 rounded-full animate-spin" />
    </div>
  ),
});

/* ── Collapse toggle button ────────────────────────────────────────────── */
function CollapseToggle({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="w-5 h-5 flex items-center justify-center rounded-full text-muted-foreground/25 hover:text-foreground/50 hover:bg-foreground/[0.06] transition-all" title={open ? 'Collapse' : 'Expand'}>
      <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? '' : '-rotate-90'}`} />
    </button>
  );
}

export default function Home() {
  useEffect(() => { document.title = 'Dashboard | Investment-X'; }, []);

  const [period, setPeriod] = useState<Period>('1Y');
  const [techRefreshing, setTechRefreshing] = useState(false);
  const [showTechInfo, setShowTechInfo] = useState(false);
  const techInfoBtnRef = useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();

  // Collapsible sections
  const [techOpen, setTechOpen] = useState(true);
  const [briefingOpen, setBriefingOpen] = useState(true);
  const [marketsOpen, setMarketsOpen] = useState(true);

  // Read computed_at from the shared technicals query cache (lightweight — only S&P 500 OHLCV included)
  const { data: techData } = useQuery<any>({
    queryKey: ['technicals', 'S&P 500'],
    queryFn: () => apiFetchJson('/api/macro/technicals?index=S%26P%20500'),
    staleTime: 300_000,
    gcTime: 600_000,
    refetchOnWindowFocus: false,
  });
  const computedAt = techData?.computed_at
    ? new Date(techData.computed_at).toLocaleString('en-US', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: true,
      })
    : null;

  const handleTechRefresh = useCallback(async () => {
    setTechRefreshing(true);
    try {
      await apiFetchJson('/api/macro/technicals/refresh', { method: 'POST' });
      await queryClient.invalidateQueries({ queryKey: ['technicals'], exact: false });
    } catch { /* ignore */ }
    setTechRefreshing(false);
  }, [queryClient]);

  return (
    <AppShell hideFooter>
      <div className="bg-background overflow-y-auto">
        <div className="max-w-[1600px] mx-auto p-2 sm:p-3 lg:p-4 space-y-3">

          {/* ═══ Technicals ═══════════════════════════════════════════ */}
          <section className="dashboard-section overflow-hidden animate-fade-in">
            <div className="section-header flex-wrap">
              <span className="section-title">Technicals</span>
              <CollapseToggle open={techOpen} onClick={() => setTechOpen(p => !p)} />
              <button
                ref={techInfoBtnRef}
                onMouseEnter={() => setShowTechInfo(true)}
                onMouseLeave={() => setShowTechInfo(false)}
                onClick={() => setShowTechInfo(p => !p)}
                className="w-5 h-5 flex items-center justify-center rounded-full text-muted-foreground/30 hover:text-primary/70 hover:bg-primary/[0.08] transition-colors"
                title="About technical indicators"
              >
                <Info className="w-3.5 h-3.5" />
              </button>
              {showTechInfo && typeof document !== 'undefined' && createPortal(
                <div
                  className="fixed z-[9999] w-72 rounded-[var(--radius)] border border-border/40 bg-popover shadow-xl p-3"
                  style={(() => {
                    const r = techInfoBtnRef.current?.getBoundingClientRect();
                    return r ? { top: r.bottom + 6, left: r.left } : { top: 0, left: 0, display: 'none' };
                  })()}
                  onMouseEnter={() => setShowTechInfo(true)}
                  onMouseLeave={() => setShowTechInfo(false)}
                >
                  <p className="text-[10px] font-semibold text-foreground/70 mb-2 tracking-wide uppercase">Chart Indicators</p>
                  {[
                    ['Candlesticks', 'OHLC price action. Green = bullish close, Red = bearish close.'],
                    ['EMA 21 / 55', 'Exponential Moving Averages. Price above both = uptrend. A 21 crossing above 55 = bullish signal.'],
                    ['Ichimoku Cloud', 'Tenkan (blue) & Kijun (brown) lines with cloud fill. Price above cloud = bullish; below = bearish.'],
                    ['MACD (12,26,9)', 'Momentum oscillator. Line above signal = bullish. Histogram shows strength of the trend.'],
                    ['ROC (SMA 9)', 'Rate of Change smoothed. Green bars = positive momentum, Red = negative. Divergence from price warns of reversal.'],
                    ['VOMO Score', 'Volatility-adjusted momentum composite. Above +1 = bullish, below −1 = bearish.'],
                  ].map(([title, desc]) => (
                    <div key={title} className="mb-2 last:mb-0">
                      <span className="text-[9px] font-mono font-semibold text-primary/80">{title}</span>
                      <p className="text-[9px] text-muted-foreground/60 leading-[1.45] mt-0.5">{desc}</p>
                    </div>
                  ))}
                </div>,
                document.body,
              )}
              <div className="flex-1 min-w-[8px]" />
              {techOpen && (
                <div className="flex items-center gap-1">
                  <div className="flex items-center gap-0.5 p-0.5 rounded-[var(--radius)] bg-foreground/[0.04]">
                    {PERIODS.map(p => (
                      <button key={p} onClick={() => setPeriod(p)}
                        className={p === period
                          ? 'h-5 px-1.5 rounded-[calc(var(--radius)-2px)] text-[9px] font-bold bg-foreground text-background transition-all duration-150'
                          : 'h-5 px-1.5 rounded-[calc(var(--radius)-2px)] text-[9px] font-medium text-muted-foreground/50 hover:text-foreground hover:bg-foreground/[0.05] transition-all duration-150'
                        }>
                        {p}
                      </button>
                    ))}
                  </div>
                  {computedAt && (
                    <span className="inline-flex items-center gap-1 text-muted-foreground/30 font-mono text-[9px] whitespace-nowrap" title={`Last updated: ${computedAt}`}>
                      <Clock className="w-2.5 h-2.5 shrink-0" />
                      {computedAt}
                    </span>
                  )}
                  <button onClick={handleTechRefresh} disabled={techRefreshing} className="btn-icon" title="Refresh technical data">
                    <RefreshCw className={`w-2.5 h-2.5 ${techRefreshing ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              )}
            </div>
            {techOpen && <Technicals period={period} />}
          </section>

          {/* ═══ Two-column: Briefing + Markets ═══════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-3">

            {/* ── Briefing ─────────────────────────────────────────── */}
            <section className="dashboard-section overflow-hidden flex flex-col animate-fade-in stagger-2" style={briefingOpen ? { maxHeight: 520 } : undefined}>
              <Briefing embedded collapsed={!briefingOpen} onToggleCollapse={() => setBriefingOpen(p => !p)} />
            </section>

            {/* ── Markets ──────────────────────────────────────────── */}
            <section className="dashboard-section overflow-hidden flex flex-col animate-fade-in stagger-3" style={marketsOpen ? { maxHeight: 520 } : undefined}>
              <MarketPulse collapsed={!marketsOpen} onToggleCollapse={() => setMarketsOpen(p => !p)} />
            </section>

          </div>

        </div>
      </div>
    </AppShell>
  );
}
