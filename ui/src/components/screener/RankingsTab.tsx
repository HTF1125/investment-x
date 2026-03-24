'use client';

import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, Search } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { SORTABLE_COLUMNS, vomoColor, trendColor, fmtNum } from './constants';
import type { ScreenerStock, SortField } from './types';

interface Props {
  stocks: ScreenerStock[];
  isLoading: boolean;
  error?: string;
}

export default function RankingsTab({ stocks, isLoading, error }: Props) {
  const { theme } = useTheme();
  const [sortField, setSortField] = useState<SortField>('vomo_composite');
  const [sortAsc, setSortAsc] = useState(false);
  const [search, setSearch] = useState('');
  const [trendOnly, setTrendOnly] = useState(false);
  const [minFunds, setMinFunds] = useState(0);

  const filtered = useMemo(() => {
    let result = [...stocks];
    if (search) {
      const q = search.toUpperCase();
      result = result.filter(s => s.symbol.includes(q));
    }
    if (trendOnly) {
      result = result.filter(s => s.trend_confirmed);
    }
    if (minFunds > 0) {
      result = result.filter(s => s.fund_count >= minFunds);
    }
    result.sort((a, b) => {
      const av = a[sortField] ?? -Infinity;
      const bv = b[sortField] ?? -Infinity;
      if (typeof av === 'string' && typeof bv === 'string') {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return result;
  }, [stocks, search, trendOnly, minFunds, sortField, sortAsc]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-[10px] text-muted-foreground/50 tracking-widest uppercase">
            Computing VOMO scores
          </span>
          <span className="text-[9px] text-muted-foreground/30 mt-1">First load may take 1-2 minutes</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card p-6 text-center">
        <p className="text-[12px] text-destructive/80 mb-1">Failed to load screener data</p>
        <p className="text-[10px] text-muted-foreground/40 font-mono">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[180px] max-w-[280px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search symbol..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 pl-8 pr-3 border border-border/50 rounded-[var(--radius)] text-[12px] focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          />
        </div>

        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={trendOnly}
            onChange={e => setTrendOnly(e.target.checked)}
            className="w-3.5 h-3.5 rounded border-border/50 accent-primary"
          />
          <span className="text-[11px] text-muted-foreground">Trend confirmed</span>
        </label>

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-muted-foreground/50 font-mono uppercase">Min funds</span>
          <input
            type="number"
            min={0}
            max={15}
            value={minFunds}
            onChange={e => setMinFunds(Math.max(0, parseInt(e.target.value) || 0))}
            className="w-14 h-7 px-2 border border-border/50 rounded-[var(--radius)] text-[12px] text-center focus:outline-none focus:border-primary/50"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          />
        </div>

        <span className="text-[10px] font-mono text-muted-foreground/35 ml-auto">
          {filtered.length} / {stocks.length} stocks
        </span>
      </div>

      {/* Table */}
      <div className="panel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border/30">
                {SORTABLE_COLUMNS.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-2.5 py-2 text-left text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 cursor-pointer hover:text-foreground transition-colors select-none whitespace-nowrap"
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {sortField === col.key && (
                        sortAsc
                          ? <ChevronUp className="w-3 h-3 text-primary" />
                          : <ChevronDown className="w-3 h-3 text-primary" />
                      )}
                    </span>
                  </th>
                ))}
                <th className="px-2.5 py-2 text-left text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap">
                  Trend
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(stock => (
                <tr
                  key={stock.symbol}
                  className="border-b border-border/15 hover:bg-foreground/[0.02] transition-colors"
                >
                  <td className="px-2.5 py-1.5 text-muted-foreground/40 font-mono tabular-nums">
                    {stock.rank}
                  </td>
                  <td className="px-2.5 py-1.5 font-semibold text-foreground">
                    {stock.symbol}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/80">
                    ${stock.price.toFixed(2)}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${vomoColor(stock.vomo_1m)}`}>
                    {fmtNum(stock.vomo_1m, 2)}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${vomoColor(stock.vomo_6m)}`}>
                    {fmtNum(stock.vomo_6m, 2)}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${vomoColor(stock.vomo_1y)}`}>
                    {fmtNum(stock.vomo_1y, 2)}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums font-semibold ${vomoColor(stock.vomo_composite)}`}>
                    {fmtNum(stock.vomo_composite, 2)}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                    {stock.fund_count > 0 && (
                      <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-[4px] bg-primary/10 text-primary text-[10px] font-bold">
                        {stock.fund_count}
                      </span>
                    )}
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/60">
                    {stock.fwd_eps_growth !== null ? `${(stock.fwd_eps_growth * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${(stock.return_1m ?? 0) >= 0 ? 'text-success/80' : 'text-destructive/80'}`}>
                    {fmtNum(stock.return_1m)}%
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${(stock.return_6m ?? 0) >= 0 ? 'text-success/80' : 'text-destructive/80'}`}>
                    {fmtNum(stock.return_6m)}%
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums ${(stock.return_1y ?? 0) >= 0 ? 'text-success/80' : 'text-destructive/80'}`}>
                    {fmtNum(stock.return_1y)}%
                  </td>
                  <td className="px-2.5 py-1.5">
                    <div className="flex items-center gap-1">
                      <div className={`w-2 h-2 rounded-full ${trendColor(stock.short_trend, stock.long_trend)}`} title={
                        stock.trend_confirmed ? 'Above 50d & 200d SMA' :
                        stock.short_trend ? 'Above 50d SMA only' :
                        stock.long_trend ? 'Above 200d SMA only' :
                        'Below both SMAs'
                      } />
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={13} className="px-4 py-8 text-center text-muted-foreground/40 text-[12px]">
                    {stocks.length === 0 ? 'No screener data yet. Run the 13F collector first.' : 'No stocks match filters.'}
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
