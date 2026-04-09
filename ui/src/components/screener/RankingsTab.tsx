'use client';

import { useState, useMemo, useCallback, useRef, useEffect, Fragment } from 'react';
import { ChevronUp, ChevronDown, Search, Settings2, Download } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { SORTABLE_COLUMNS, DEFAULT_VISIBLE, vomoColor, vomoBackground, trendColor, fmtNum, fmtMarketCap, fmtVolume } from './constants';
import Sparkline from './Sparkline';
import SummaryStats from './SummaryStats';
import StockDetailPanel from './StockDetailPanel';
import type { ScreenerStock, FlowEntry, SortField } from './types';

interface Props {
  stocks: ScreenerStock[];
  flows: FlowEntry[];
  isLoading: boolean;
  error?: string;
}

export default function RankingsTab({ stocks, flows, isLoading, error }: Props) {
  const { theme } = useTheme();
  const [sortField, setSortField] = useState<SortField>('vomo_composite');
  const [sortAsc, setSortAsc] = useState(false);
  const [search, setSearch] = useState('');
  const [trendOnly, setTrendOnly] = useState(false);
  const [minFunds, setMinFunds] = useState(0);
  const [sectorFilter, setSectorFilter] = useState('');
  const [visibleCols, setVisibleCols] = useState<Set<SortField>>(new Set(DEFAULT_VISIBLE));
  const [showColMenu, setShowColMenu] = useState(false);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const colMenuRef = useRef<HTMLDivElement>(null);

  // Close column menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (colMenuRef.current && !colMenuRef.current.contains(e.target as Node)) {
        setShowColMenu(false);
      }
    };
    if (showColMenu) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showColMenu]);

  const sectors = useMemo(() => {
    const set = new Set<string>();
    stocks.forEach(s => { if (s.sector) set.add(s.sector); });
    return Array.from(set).sort();
  }, [stocks]);

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
    if (sectorFilter) {
      result = result.filter(s => s.sector === sectorFilter);
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
  }, [stocks, search, trendOnly, minFunds, sectorFilter, sortField, sortAsc]);

  const handleSort = (field: SortField) => {
    if (field === sortField) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };

  const toggleCol = (key: SortField) => {
    setVisibleCols(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const exportCsv = useCallback(() => {
    const headers = ['Rank', 'Symbol', 'Price', 'VOMO Composite', 'VOMO 1M', 'VOMO 6M', 'VOMO 1Y',
      'Funds', 'RS%', 'Sector', 'Mkt Cap', 'Fwd EPS', 'Return 1M', 'Return 6M', 'Return 1Y',
      'DD 52w', 'Avg Vol 30d', 'Trend Confirmed'];
    const rows = filtered.map(s => [
      s.rank, s.symbol, s.price, s.vomo_composite, s.vomo_1m, s.vomo_6m, s.vomo_1y,
      s.fund_count, s.rs_percentile, s.sector ?? '', s.market_cap ?? '',
      s.fwd_eps_growth !== null ? (s.fwd_eps_growth * 100).toFixed(1) + '%' : '',
      s.return_1m, s.return_6m, s.return_1y,
      s.drawdown_52w, s.avg_volume_30d, s.trend_confirmed,
    ].join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vomo_screener_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filtered]);

  const activeCols = SORTABLE_COLUMNS.filter(c => visibleCols.has(c.key));
  // +2 for sparkline and trend columns
  const totalColSpan = activeCols.length + 2;

  const cs = theme === 'light' ? 'light' : 'dark';
  const formStyle = { colorScheme: cs, backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-[11.5px] text-muted-foreground/50 tracking-widest uppercase">
            Computing VOMO scores
          </span>
          <span className="text-[11px] text-muted-foreground/30 mt-1">First load may take 1-2 minutes</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card p-6 text-center">
        <p className="text-[13px] text-destructive/80 mb-1">Failed to load screener data</p>
        <p className="text-[11.5px] text-muted-foreground/40 font-mono">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Summary stats */}
      <SummaryStats stocks={stocks} />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[180px] max-w-[280px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search symbol..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 pl-8 pr-3 border border-border/50 rounded-[var(--radius)] text-[13px] focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            style={formStyle}
          />
        </div>

        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={trendOnly}
            onChange={e => setTrendOnly(e.target.checked)}
            className="w-3.5 h-3.5 rounded border-border/50 accent-primary"
          />
          <span className="text-[12.5px] text-muted-foreground">Trend confirmed</span>
        </label>

        <div className="flex items-center gap-1.5">
          <span className="text-[11.5px] text-muted-foreground/50 font-mono uppercase">Min funds</span>
          <input
            type="number"
            min={0}
            max={15}
            value={minFunds}
            onChange={e => setMinFunds(Math.max(0, parseInt(e.target.value) || 0))}
            className="w-14 h-7 px-2 border border-border/50 rounded-[var(--radius)] text-[13px] text-center focus:outline-none focus:border-primary/50"
            style={formStyle}
          />
        </div>

        {/* Sector filter */}
        {sectors.length > 0 && (
          <select
            value={sectorFilter}
            onChange={e => setSectorFilter(e.target.value)}
            className="h-7 px-2 border border-border/50 rounded-[var(--radius)] text-[12.5px] focus:outline-none focus:border-primary/50"
            style={formStyle}
          >
            <option value="">All sectors</option>
            {sectors.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        )}

        <div className="flex items-center gap-1 ml-auto">
          {/* Column toggle */}
          <div className="relative" ref={colMenuRef}>
            <button
              onClick={() => setShowColMenu(!showColMenu)}
              className="btn-icon flex items-center justify-center text-muted-foreground/50 hover:text-foreground transition-colors"
              title="Toggle columns"
            >
              <Settings2 className="w-3.5 h-3.5" />
            </button>
            {showColMenu && (
              <div className="absolute right-0 top-full mt-1 z-30 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-2 min-w-[160px]">
                <div className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted-foreground/40 mb-1.5 px-1">Columns</div>
                {SORTABLE_COLUMNS.map(col => (
                  <label key={col.key} className="flex items-center gap-2 px-1 py-0.5 cursor-pointer hover:bg-foreground/[0.03] rounded">
                    <input
                      type="checkbox"
                      checked={visibleCols.has(col.key)}
                      onChange={() => toggleCol(col.key)}
                      className="w-3 h-3 rounded accent-primary"
                    />
                    <span className="text-[12.5px] text-foreground/70">{col.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Export CSV */}
          <button
            onClick={exportCsv}
            className="btn-icon flex items-center justify-center text-muted-foreground/50 hover:text-foreground transition-colors"
            title="Export CSV"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <span className="text-[11.5px] font-mono text-muted-foreground/35 ml-2">
            {filtered.length} / {stocks.length}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="panel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border/30">
                {activeCols.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-2.5 py-2 text-left text-[11.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 cursor-pointer hover:text-foreground transition-colors select-none whitespace-nowrap"
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
                <th className="px-2 py-2 text-left text-[11.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap">
                  3M
                </th>
                <th className="px-2 py-2 text-left text-[11.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap">
                  Trend
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(stock => {
                const isExpanded = expandedSymbol === stock.symbol;
                return (
                  <Fragment key={stock.symbol}>
                    <tr
                      onClick={() => setExpandedSymbol(isExpanded ? null : stock.symbol)}
                      className={`border-b border-border/15 hover:bg-foreground/[0.02] transition-colors cursor-pointer ${isExpanded ? 'bg-foreground/[0.02]' : ''}`}
                    >
                      {activeCols.map(col => (
                        <td key={col.key} className={`px-2.5 py-1.5 font-mono tabular-nums ${cellClass(col.key, stock)}`}>
                          {renderCell(col.key, stock)}
                        </td>
                      ))}
                      {/* Sparkline */}
                      <td className="px-2 py-1.5">
                        {stock.sparkline_3m && stock.sparkline_3m.length > 1 ? (
                          <Sparkline data={stock.sparkline_3m} positive={(stock.return_1m ?? 0) >= 0} />
                        ) : null}
                      </td>
                      {/* Trend */}
                      <td className="px-2 py-1.5">
                        <div className={`w-2 h-2 rounded-full ${trendColor(stock.short_trend, stock.long_trend)}`} title={
                          stock.trend_confirmed ? 'Above 50d & 200d SMA' :
                          stock.short_trend ? 'Above 50d SMA only' :
                          stock.long_trend ? 'Above 200d SMA only' :
                          'Below both SMAs'
                        } />
                      </td>
                    </tr>
                    {isExpanded && (
                      <StockDetailPanel
                        stock={stock}
                        flows={flows}
                        colSpan={totalColSpan}
                      />
                    )}
                  </Fragment>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={totalColSpan} className="px-4 py-8 text-center text-muted-foreground/40 text-[13px]">
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


function cellClass(key: SortField, stock: ScreenerStock): string {
  switch (key) {
    case 'rank':
      return 'text-muted-foreground/40';
    case 'symbol':
      return 'font-semibold text-foreground !font-sans';
    case 'price':
      return 'text-foreground/80';
    case 'vomo_1m':
    case 'vomo_6m':
    case 'vomo_1y':
      return `${vomoColor(stock[key])} ${vomoBackground(stock[key])}`;
    case 'vomo_composite':
      return `font-semibold ${vomoColor(stock.vomo_composite)} ${vomoBackground(stock.vomo_composite)}`;
    case 'fund_count':
      return '';
    case 'rs_percentile':
      return (stock.rs_percentile ?? 0) >= 80 ? 'text-success/80' : (stock.rs_percentile ?? 50) <= 20 ? 'text-destructive/80' : 'text-foreground/70';
    case 'drawdown_52w':
      return (stock.drawdown_52w ?? 0) < -20 ? 'text-destructive/80' : 'text-foreground/60';
    case 'fwd_eps_growth':
      return 'text-foreground/60';
    case 'return_1m':
    case 'return_6m':
    case 'return_1y':
      return (stock[key] ?? 0) >= 0 ? 'text-success/80' : 'text-destructive/80';
    case 'market_cap':
      return 'text-foreground/60';
    case 'avg_volume_30d':
    case 'relative_volume':
      return 'text-foreground/60';
    default:
      return 'text-foreground/70';
  }
}

function renderCell(key: SortField, stock: ScreenerStock): React.ReactNode {
  switch (key) {
    case 'rank':
      return stock.rank;
    case 'symbol':
      return stock.symbol;
    case 'price':
      return `$${stock.price.toFixed(2)}`;
    case 'vomo_1m':
      return fmtNum(stock.vomo_1m, 2);
    case 'vomo_6m':
      return fmtNum(stock.vomo_6m, 2);
    case 'vomo_1y':
      return fmtNum(stock.vomo_1y, 2);
    case 'vomo_composite':
      return fmtNum(stock.vomo_composite, 2);
    case 'fund_count':
      return stock.fund_count > 0 ? (
        <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-[4px] bg-primary/10 text-primary text-[11.5px] font-bold">
          {stock.fund_count}
        </span>
      ) : null;
    case 'rs_percentile':
      return stock.rs_percentile !== null ? stock.rs_percentile : '-';
    case 'drawdown_52w':
      return stock.drawdown_52w !== null ? `${stock.drawdown_52w}%` : '-';
    case 'fwd_eps_growth':
      return stock.fwd_eps_growth !== null ? `${(stock.fwd_eps_growth * 100).toFixed(0)}%` : '-';
    case 'return_1m':
      return stock.return_1m !== null ? `${fmtNum(stock.return_1m)}%` : '-';
    case 'return_6m':
      return stock.return_6m !== null ? `${fmtNum(stock.return_6m)}%` : '-';
    case 'return_1y':
      return stock.return_1y !== null ? `${fmtNum(stock.return_1y)}%` : '-';
    case 'market_cap':
      return fmtMarketCap(stock.market_cap);
    case 'avg_volume_30d':
      return fmtVolume(stock.avg_volume_30d);
    case 'relative_volume':
      return stock.relative_volume !== null ? `${stock.relative_volume}x` : '-';
    default:
      return '-';
  }
}
