'use client';

import { useMemo } from 'react';
import { getApiCode } from '@/lib/buildChartFigure';
import { COLORWAY } from '@/lib/chartTheme';
import { fmtNum } from './helpers';
import type { SelectedSeries } from './types';

export default function StatsPanel({
  rawData,
  visibleSeries,
  selectedSeries,
}: {
  rawData: Record<string, (string | number | null)[]>;
  visibleSeries: SelectedSeries[];
  selectedSeries: SelectedSeries[];
}) {
  const stats = useMemo(() => {
    if (!rawData?.Date) return [];
    return visibleSeries.map((s) => {
      const apiCode = getApiCode(s);
      let values = ((rawData[apiCode] || []) as (number | null)[]);
      if (s.transform === 'log') {
        values = values.map((v) => (v != null && v > 0 ? Math.log(v) : null));
      }
      const nums = values.filter((v): v is number => v != null);
      const color = s.color || COLORWAY[selectedSeries.indexOf(s) % COLORWAY.length];
      if (nums.length === 0) return { code: s.code, name: s.name, color, last: null, chg: null, chgPct: null, min: null, max: null, mean: null, std: null };
      const last = nums[nums.length - 1];
      const prev = nums.length > 1 ? nums[nums.length - 2] : null;
      const chg = prev != null ? last - prev : null;
      const chgPct = prev != null && prev !== 0 ? ((last - prev) / prev) * 100 : null;
      const min = Math.min(...nums);
      const max = Math.max(...nums);
      const mean = nums.reduce((a, b) => a + b, 0) / nums.length;
      const std = Math.sqrt(nums.reduce((a, b) => a + (b - mean) ** 2, 0) / nums.length);
      return { code: s.code, name: s.name, color, last, chg, chgPct, min, max, mean, std };
    });
  }, [rawData, visibleSeries, selectedSeries]);

  if (stats.length === 0) return null;

  return (
    <div className="text-[11px] font-mono">
      <div className="flex items-center gap-0 px-2 py-0.5 border-b border-border/20 bg-foreground/[0.02]">
        <span className="w-3 shrink-0" />
        <span className="flex-1 min-w-0 text-[9.5px] uppercase tracking-[0.1em] text-muted-foreground/40 font-semibold">{'\u2014'}</span>
        <span className="w-[50px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">Last</span>
        <span className="w-[42px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">{'\u0394'}%</span>
        <span className="w-[42px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">Lo</span>
        <span className="w-[42px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">Hi</span>
        <span className="w-[42px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">{'\u03BC'}</span>
        <span className="w-[42px] text-right text-[9.5px] uppercase tracking-[0.08em] text-muted-foreground/40 font-semibold shrink-0">{'\u03C3'}</span>
      </div>
      {stats.map((row, i) => (
        <div key={row.code} className={`flex items-center gap-0 px-2 py-0.5 border-b border-border/8 hover:bg-foreground/[0.02] transition-colors ${i % 2 === 1 ? 'bg-foreground/[0.01]' : ''}`}>
          <span className="w-2 h-2 rounded-full shrink-0 mr-1" style={{ backgroundColor: row.color }} />
          <span className="flex-1 min-w-0 text-foreground/60 truncate" title={row.name}>{row.code}</span>
          <span className="w-[50px] text-right tabular-nums text-foreground shrink-0">{fmtNum(row.last)}</span>
          <span className={`w-[42px] text-right tabular-nums font-medium shrink-0 ${row.chgPct != null && row.chgPct >= 0 ? 'text-success' : 'text-destructive'}`}>
            {row.chgPct != null ? (row.chgPct >= 0 ? '+' : '') + fmtNum(row.chgPct, 1) + '%' : '\u2014'}
          </span>
          <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.min)}</span>
          <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.max)}</span>
          <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.mean)}</span>
          <span className="w-[42px] text-right tabular-nums text-foreground/50 shrink-0">{fmtNum(row.std)}</span>
        </div>
      ))}
    </div>
  );
}
