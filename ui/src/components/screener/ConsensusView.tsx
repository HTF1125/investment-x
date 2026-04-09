'use client';

import { useState, useMemo } from 'react';
import { Search, ChevronUp, ChevronDown } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { vomoColor, fmtMarketCap, fmtUsd, fmtNum, CONSENSUS_COLORS } from './constants';
import type { ConsensusEntry } from './types';

interface Props {
  consensus: ConsensusEntry[];
  isLoading: boolean;
  error?: string;
}

type ConsensusSortField = 'fund_count' | 'total_value_usd' | 'vomo_composite' | 'symbol';

export default function ConsensusView({ consensus, isLoading, error }: Props) {
  const { theme } = useTheme();
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<ConsensusSortField>('fund_count');
  const [sortAsc, setSortAsc] = useState(false);

  const filtered = useMemo(() => {
    let result = [...consensus];
    if (search) {
      const q = search.toUpperCase();
      result = result.filter(c => c.symbol.includes(q));
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
  }, [consensus, search, sortField, sortAsc]);

  const handleSort = (field: ConsensusSortField) => {
    if (field === sortField) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-[11.5px] text-muted-foreground/50 tracking-widest uppercase">Loading consensus</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card p-6 text-center">
        <p className="text-[13px] text-destructive/80 mb-1">Failed to load consensus data</p>
        <p className="text-[11.5px] text-muted-foreground/40 font-mono">{error}</p>
      </div>
    );
  }

  const SortIcon = ({ field }: { field: ConsensusSortField }) => {
    if (sortField !== field) return null;
    return sortAsc ? <ChevronUp className="w-3 h-3 text-primary" /> : <ChevronDown className="w-3 h-3 text-primary" />;
  };

  const columns: { key: ConsensusSortField | 'actions' | 'funds_list' | 'sector'; label: string; sortable: boolean; title?: string }[] = [
    { key: 'symbol', label: 'Symbol', sortable: true },
    { key: 'fund_count', label: 'Funds', sortable: true },
    { key: 'total_value_usd', label: 'Total Value', sortable: true },
    { key: 'funds_list', label: 'Fund Names', sortable: false },
    { key: 'actions', label: 'Actions', sortable: false },
    { key: 'sector', label: 'Sector', sortable: false },
    { key: 'vomo_composite', label: 'VOMO', sortable: true, title: 'Volatility Momentum — composite signal measuring value and momentum across timeframes' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="relative min-w-[180px] max-w-[280px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/40" />
          <input
            type="text"
            placeholder="Search symbol..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full h-8 pl-8 pr-3 border border-border/50 rounded-[var(--radius)] text-[13px] focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
            style={{ colorScheme: theme === 'light' ? 'light' : 'dark', backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}
          />
        </div>
        <span className="text-[11.5px] font-mono text-muted-foreground/35 ml-auto">
          {filtered.length} stocks
        </span>
      </div>

      <div className="panel-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border/30">
                {columns.map(col => (
                  <th
                    key={col.key}
                    onClick={col.sortable ? () => handleSort(col.key as ConsensusSortField) : undefined}
                    title={col.title}
                    className={`px-2.5 py-2 text-left text-[11.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap ${col.sortable ? 'cursor-pointer hover:text-foreground transition-colors' : ''} select-none`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.sortable && <SortIcon field={col.key as ConsensusSortField} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(entry => (
                <tr key={entry.symbol} className="border-b border-border/15 hover:bg-foreground/[0.02] transition-colors">
                  <td className="px-2.5 py-1.5 font-semibold text-foreground">{entry.symbol}</td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums">
                    <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-[4px] bg-primary/10 text-primary text-[11.5px] font-bold">
                      {entry.fund_count}
                    </span>
                  </td>
                  <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                    {fmtUsd(entry.total_value_usd)}
                  </td>
                  <td className="px-2.5 py-1.5 text-foreground/60 max-w-[200px]">
                    <span className="text-[11.5px] truncate block" title={entry.fund_names.join(', ')}>
                      {entry.fund_names.map(n => n.split(' ')[0]).join(', ')}
                    </span>
                  </td>
                  <td className="px-2.5 py-1.5">
                    <div className="flex items-center gap-1.5">
                      {Object.entries(entry.actions).map(([action, count]) => (
                        <span key={action} className={`text-[11px] font-mono font-semibold uppercase ${
                          action === 'NEW' || action === 'INCREASED' ? 'text-success/80' :
                          action === 'SOLD' || action === 'DECREASED' ? 'text-destructive/80' :
                          'text-muted-foreground/50'
                        }`}>
                          {count}{action.charAt(0)}
                        </span>
                      ))}
                      <span className={`text-[11px] font-semibold ml-1 ${CONSENSUS_COLORS[entry.consensus_label] || ''}`}>
                        {entry.consensus_label}
                      </span>
                    </div>
                  </td>
                  <td className="px-2.5 py-1.5 text-foreground/60 text-[12.5px]">
                    {entry.sector || '-'}
                  </td>
                  <td className={`px-2.5 py-1.5 font-mono tabular-nums font-semibold ${vomoColor(entry.vomo_composite)}`}>
                    {fmtNum(entry.vomo_composite, 2)}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground/40 text-[13px]">
                    No consensus data available.
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
