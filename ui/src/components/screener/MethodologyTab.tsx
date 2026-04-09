'use client';

export default function MethodologyTab() {
  return (
    <div className="space-y-4 max-w-3xl">
      {/* Overview */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">What is VOMO?</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-3">
          VOMO (<span className="font-semibold text-foreground">V</span>olatility-adjusted
          M<span className="font-semibold text-foreground">o</span>mentum) measures risk-adjusted
          momentum by dividing a stock&apos;s return over a period by its average true range (ATR) over the
          same period. Inspired by Scott Bennett&apos;s methodology at InvestWithRules.com.
        </p>
        <div className="bg-foreground/[0.03] border border-border/30 rounded-[var(--radius)] p-3 font-mono text-[13px] text-foreground/80">
          VOMO = Return% / Average ATR%
        </div>
      </div>

      {/* Timeframes */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">Scoring Timeframes</h3>
        <div className="space-y-2">
          <div className="flex items-start gap-3">
            <span className="stat-label w-16 pt-0.5 shrink-0">1M (21d)</span>
            <p className="text-[13px] text-muted-foreground leading-relaxed">
              Short-term momentum. Captures recent price action relative to near-term volatility.
              Weighted <span className="font-mono text-foreground/70">20%</span> in composite.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <span className="stat-label w-16 pt-0.5 shrink-0">6M (126d)</span>
            <p className="text-[13px] text-muted-foreground leading-relaxed">
              Medium-term trend strength. The sweet spot for institutional momentum.
              Weighted <span className="font-mono text-foreground/70">40%</span> in composite.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <span className="stat-label w-16 pt-0.5 shrink-0">1Y (252d)</span>
            <p className="text-[13px] text-muted-foreground leading-relaxed">
              Long-term trend persistence. Filters out mean-reverting noise.
              Weighted <span className="font-mono text-foreground/70">40%</span> in composite.
            </p>
          </div>
        </div>
        <div className="mt-3 bg-foreground/[0.03] border border-border/30 rounded-[var(--radius)] p-3 font-mono text-[13px] text-foreground/80">
          Composite = 0.2 * VOMO_1M + 0.4 * VOMO_6M + 0.4 * VOMO_1Y
        </div>
      </div>

      {/* ATR */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">Average True Range (ATR)</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-2">
          ATR measures volatility using the maximum of three values per day:
        </p>
        <ul className="text-[13px] text-muted-foreground leading-relaxed list-disc pl-5 space-y-1">
          <li>High - Low (daily range)</li>
          <li>|High - Previous Close| (gap up)</li>
          <li>|Low - Previous Close| (gap down)</li>
        </ul>
        <p className="text-[13px] text-muted-foreground leading-relaxed mt-2">
          We use a 14-day rolling average, then express ATR as a percentage of price for
          cross-stock comparability.
        </p>
      </div>

      {/* Trend Confirmation */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">Trend Confirmation</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-2">
          Two simple moving average checks:
        </p>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-success" />
            <span className="text-[13px] text-foreground/80">Both confirmed: Price {'>'} 50d SMA and {'>'} 200d SMA</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-warning" />
            <span className="text-[13px] text-foreground/80">Partial: Only one SMA confirmed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-destructive" />
            <span className="text-[13px] text-foreground/80">No confirmation: Price below both SMAs</span>
          </div>
        </div>
      </div>

      {/* 13F Institutional Flows */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">13F Institutional Flows</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-2">
          The screener universe is built from SEC 13-F filings of 15 tracked mega funds,
          including Bridgewater, Renaissance Technologies, Berkshire Hathaway, Citadel,
          and others. The &ldquo;Funds&rdquo; column shows how many of these institutions hold a given stock.
        </p>
        <p className="text-[13px] text-muted-foreground leading-relaxed">
          Stocks held by multiple top institutions with high VOMO scores and confirmed
          trends represent the strongest intersection of institutional conviction and
          price momentum.
        </p>
      </div>

      {/* Data Sources */}
      <div className="panel-card p-4">
        <h3 className="text-[13px] font-semibold text-foreground mb-2">Data Sources</h3>
        <div className="space-y-1.5 text-[13px] text-muted-foreground">
          <div className="flex gap-2">
            <span className="font-mono text-foreground/50 w-24 shrink-0">Holdings</span>
            <span>SEC EDGAR 13-F filings (quarterly)</span>
          </div>
          <div className="flex gap-2">
            <span className="font-mono text-foreground/50 w-24 shrink-0">Prices</span>
            <span>Yahoo Finance (daily OHLCV, 2-year history)</span>
          </div>
          <div className="flex gap-2">
            <span className="font-mono text-foreground/50 w-24 shrink-0">Earnings</span>
            <span>Yahoo Finance growth estimates (next year forward EPS)</span>
          </div>
          <div className="flex gap-2">
            <span className="font-mono text-foreground/50 w-24 shrink-0">Refresh</span>
            <span>Recomputed daily at 23:00 UTC, cached for 6 hours</span>
          </div>
        </div>
      </div>
    </div>
  );
}
