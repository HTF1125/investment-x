'use client';

import Sparkline from './Sparkline';
import { vomoColor, fmtNum, fmtMarketCap, trendColor } from './constants';
import type { ScreenerStock, FlowEntry } from './types';

interface Props {
  stock: ScreenerStock;
  flows: FlowEntry[];
  colSpan: number;
}

export default function StockDetailPanel({ stock, flows, colSpan }: Props) {
  const fundFlows = flows.filter(f => f.symbol === stock.symbol);
  const ret3m = stock.return_1m !== null && stock.return_6m !== null
    ? (stock.return_6m + stock.return_1m) / 2
    : stock.return_6m ?? stock.return_1m;
  const sparkPositive = (ret3m ?? 0) >= 0;

  return (
    <tr>
      <td colSpan={colSpan} className="p-0">
        <div className="bg-foreground/[0.015] border-t border-border/20 px-4 py-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* Left: metrics */}
            <div className="space-y-2">
              <div className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-1">
                Metrics
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[13px]">
                <Metric label="Composite" value={fmtNum(stock.vomo_composite, 2)} className={vomoColor(stock.vomo_composite)} />
                <Metric label="VOMO 1M" value={fmtNum(stock.vomo_1m, 2)} className={vomoColor(stock.vomo_1m)} title="Volatility Momentum — 1 month" />
                <Metric label="VOMO 6M" value={fmtNum(stock.vomo_6m, 2)} className={vomoColor(stock.vomo_6m)} title="Volatility Momentum — 6 month" />
                <Metric label="VOMO 1Y" value={fmtNum(stock.vomo_1y, 2)} className={vomoColor(stock.vomo_1y)} title="Volatility Momentum — 1 year" />
                <Metric label="Mkt Cap" value={fmtMarketCap(stock.market_cap)} />
                <Metric label="Sector" value={stock.sector || '-'} />
                <Metric label="DD 52w" value={stock.drawdown_52w !== null ? `${stock.drawdown_52w}%` : '-'} className={stock.drawdown_52w !== null && stock.drawdown_52w < -20 ? 'text-destructive/80' : ''} />
                <Metric label="RS%" value={stock.rs_percentile !== null ? `${stock.rs_percentile}` : '-'} className={stock.rs_percentile !== null && stock.rs_percentile >= 80 ? 'text-success/80' : ''} />
                <Metric label="Fwd EPS" value={stock.fwd_eps_growth !== null ? `${(stock.fwd_eps_growth * 100).toFixed(0)}%` : '-'} />
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground/50 font-mono">Trend</span>
                  <div className={`w-2 h-2 rounded-full ${trendColor(stock.short_trend, stock.long_trend)}`} />
                  <span className="text-foreground/70 font-mono">
                    {stock.trend_confirmed ? 'Confirmed' : stock.short_trend ? '50d only' : stock.long_trend ? '200d only' : 'None'}
                  </span>
                </div>
              </div>
            </div>

            {/* Middle: funds holding this stock */}
            <div>
              <div className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-1">
                Fund Holders ({fundFlows.length})
              </div>
              {fundFlows.length > 0 ? (
                <div className="space-y-1 max-h-[160px] overflow-y-auto no-scrollbar">
                  {fundFlows.map((f, i) => (
                    <div key={i} className="flex items-center justify-between text-[12.5px]">
                      <span className="text-foreground/70 truncate max-w-[200px]" title={f.fund_name}>
                        {f.fund_name.split(' ').slice(0, 2).join(' ')}
                      </span>
                      <span className={`font-mono text-[11.5px] uppercase tracking-wider font-semibold ${
                        f.action === 'NEW' || f.action === 'INCREASED' ? 'text-success/80' :
                        f.action === 'SOLD' || f.action === 'DECREASED' ? 'text-destructive/80' :
                        'text-muted-foreground/50'
                      }`}>
                        {f.action}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-[12.5px] text-muted-foreground/40">No flow data</span>
              )}
            </div>

            {/* Right: larger sparkline */}
            <div className="flex flex-col items-end justify-center">
              <div className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-1 self-start">
                3M Price
              </div>
              {stock.sparkline_3m && stock.sparkline_3m.length > 1 ? (
                <Sparkline data={stock.sparkline_3m} width={200} height={60} positive={sparkPositive} />
              ) : (
                <span className="text-[12.5px] text-muted-foreground/30">No data</span>
              )}
            </div>
          </div>
        </div>
      </td>
    </tr>
  );
}

function Metric({ label, value, className = '', title }: { label: string; value: string; className?: string; title?: string }) {
  return (
    <div className="flex items-center justify-between" title={title}>
      <span className="text-muted-foreground/50 font-mono text-[11.5px]">{label}</span>
      <span className={`font-mono tabular-nums ${className || 'text-foreground/80'}`}>{value}</span>
    </div>
  );
}
