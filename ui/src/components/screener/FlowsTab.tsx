'use client';

import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { ACTION_COLORS, vomoColor, fmtNum, fmtUsd, fmtShares } from './constants';
import type { FlowEntry } from './types';

const ACTIONS = ['ALL', 'NEW', 'INCREASED', 'DECREASED', 'SOLD'] as const;

interface Props {
  flows: FlowEntry[];
  isLoading: boolean;
  error?: string;
}

export default function FlowsTab({ flows, isLoading, error }: Props) {
  const { theme } = useTheme();
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [fundSearch, setFundSearch] = useState('');
  const [symbolSearch, setSymbolSearch] = useState('');

  const filtered = useMemo(() => {
    let result = [...flows];
    if (actionFilter !== 'ALL') {
      result = result.filter(f => f.action === actionFilter);
    }
    if (fundSearch) {
      const q = fundSearch.toLowerCase();
      result = result.filter(f => f.fund_name.toLowerCase().includes(q));
    }
    if (symbolSearch) {
      const q = symbolSearch.toUpperCase();
      result = result.filter(f => f.symbol.includes(q));
    }
    return result;
  }, [flows, actionFilter, fundSearch, symbolSearch]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-[10px] text-muted-foreground/50 tracking-widest uppercase">Loading flows</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card p-6 text-center">
        <p className="text-[12px] text-destructive/80 mb-1">Failed to load flow data</p>
        <p className="text-[10px] text-muted-foreground/40 font-mono">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Action filter pills */}
        <div className="flex gap-1">
          {ACTIONS.map(action => (
            <button
              key={action}
              onClick={() => setActionFilter(action)}
              className={`h-7 px-2.5 rounded-[var(--radius)] text-[10px] font-semibold uppercase tracking-[0.06em] transition-all ${
                actionFilter === action
                  ? 'bg-foreground text-background'
                  : 'bg-foreground/[0.04] text-muted-foreground hover:text-foreground hover:bg-foreground/[0.08]'
              }`}
            >
              {action}
            </button>
          ))}
        </div>

        <div className="relative min-w-[160px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Fund..."
            value={fundSearch}
            onChange={e => setFundSearch(e.target.value)}
            className="w-full h-7 pl-8 pr-3 border border-border/50 rounded-[var(--radius)] text-[11px] focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          />
        </div>

        <div className="relative min-w-[120px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Symbol..."
            value={symbolSearch}
            onChange={e => setSymbolSearch(e.target.value)}
            className="w-full h-7 pl-8 pr-3 border border-border/50 rounded-[var(--radius)] text-[11px] focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          />
        </div>

        <span className="text-[10px] font-mono text-muted-foreground/35 ml-auto">
          {filtered.length} flows
        </span>
      </div>

      {/* Table */}
      <div className="panel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border/30">
                {['Fund', 'Symbol', 'Action', 'Shares', 'Value', 'Change %', 'Report Date', 'VOMO'].map(h => (
                  <th key={h} className="px-2.5 py-2 text-left text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((flow, i) => (
                <tr
                  key={`${flow.fund_name}-${flow.symbol}-${i}`}
                  className="border-b border-border/15 hover:bg-foreground/[0.02] transition-colors"
                >
                  <td className="px-2.5 py-1.5 text-foreground/70 max-w-[200px] truncate" title={flow.fund_name}>
                    {flow.fund_name}
                  </td>
                  <td className="px-2.5 py-1.5 font-semibold text-foreground">
                    {flow.symbol}
                  </td>
                  <td className={`px-2.5 py-1.5 font-semibold text-[10px] uppercase tracking-wider ${ACTION_COLORS[flow.action] || 'text-muted-foreground'}`}>
                    {flow.action}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                    {fmtShares(flow.shares)}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                    {fmtUsd(flow.value_usd)}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${
                    flow.shares_change_pct !== null
                      ? flow.shares_change_pct >= 0 ? 'text-success/80' : 'text-destructive/80'
                      : 'text-muted-foreground/30'
                  }`}>
                    {flow.shares_change_pct !== null ? `${fmtNum(flow.shares_change_pct)}%` : '-'}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-muted-foreground/50">
                    {flow.report_date || '-'}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums font-semibold ${vomoColor(flow.vomo_composite)}`}>
                    {fmtNum(flow.vomo_composite, 2)}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground/40 text-[12px]">
                    {flows.length === 0 ? 'No 13F flow data yet. Run the SEC 13F collector first.' : 'No flows match filters.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
