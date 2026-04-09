'use client';

import { fmtUsd, fmtNum, vomoColor } from './constants';
import type { SectorConcentration } from './types';

interface Props {
  sectors: SectorConcentration[];
  isLoading: boolean;
}

export default function SectorBreakdown({ sectors, isLoading }: Props) {
  if (isLoading || !sectors.length) return null;

  const maxValue = Math.max(...sectors.map(s => s.total_value_usd));

  return (
    <div className="mt-4">
      <div className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-2">
        Sector Concentration
      </div>
      <div className="panel-card overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border/30">
              {['Sector', 'Stocks', 'Total Value', 'Avg VOMO', 'Avg Funds', 'Top Holdings'].map(h => (
                <th key={h} className="px-2.5 py-2 text-left text-[11.5px] font-mono uppercase tracking-[0.08em] text-muted-foreground/50 whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sectors.map(sec => (
              <tr key={sec.sector} className="border-b border-border/15 hover:bg-foreground/[0.02] transition-colors">
                <td className="px-2.5 py-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-foreground/80 font-medium">{sec.sector}</span>
                    {/* Value bar */}
                    <div className="hidden sm:block w-16 h-1.5 bg-foreground/[0.04] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary/40 rounded-full"
                        style={{ width: `${(sec.total_value_usd / maxValue) * 100}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                  {sec.stock_count}
                </td>
                <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/70">
                  {fmtUsd(sec.total_value_usd)}
                </td>
                <td className={`px-2.5 py-1.5 font-mono tabular-nums ${vomoColor(sec.avg_vomo)}`}>
                  {fmtNum(sec.avg_vomo, 2)}
                </td>
                <td className="px-2.5 py-1.5 font-mono tabular-nums text-foreground/60">
                  {sec.avg_fund_count?.toFixed(1) ?? '-'}
                </td>
                <td className="px-2.5 py-1.5 text-foreground/60 text-[12.5px]">
                  {sec.top_symbols.join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
