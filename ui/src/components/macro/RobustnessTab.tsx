'use client';

import { SectionTitle } from './SharedComponents';

// ── Hard-coded research data (from reports/robustness_analysis.md) ──

const SENSITIVITY_PARAMS = [
  { param: 'IC Lookback Window', result: 'Pass', detail: 'Alpha > 0 in 7/7 settings (3Y-10Y)' },
  { param: 'Rebalance Frequency', result: 'Pass', detail: 'Alpha > 0 in 4/4 settings (4w-26w)' },
  { param: 'Max Factor Correlation', result: 'Pass', detail: 'Alpha > 0 in 6/6 settings (0.30-0.90)' },
  { param: 'SMA Window', result: 'Pass', detail: 'Alpha > 0 in 5/5 settings (20w-60w)' },
  { param: 'Macro/Trend Split', result: 'Pass', detail: 'Alpha > 0 in 5/5 settings (100/0-0/100)' },
  { param: 'Risk-Off Allocation', result: 'Pass', detail: 'Alpha > 0 in 4/4 settings (0%-30%)' },
  { param: 'Risk-On Allocation', result: 'Pass', detail: 'Alpha > 0 in 4/4 settings (70%-100%)' },
  { param: 'Neutral-Zone Width', result: 'Pass', detail: 'Alpha > 0 in 5/5 settings (15%-45%)' },
];

const NEIGHBORHOOD = {
  mean_score: '0.998',
  min_score: '0.989',
  configs_tested: '50',
  configs_positive: '50 / 50 (100%)',
};

const PERIOD_STABILITY = [
  { period: 'A (2006-2012)', avg_alpha: '+4.12%', indices_positive: '9 / 9', avg_sharpe: '0.61' },
  { period: 'B (2012-2018)', avg_alpha: '+2.85%', indices_positive: '8 / 9', avg_sharpe: '0.49' },
  { period: 'C (2018-2024)', avg_alpha: '+3.18%', indices_positive: '9 / 9', avg_sharpe: '0.58' },
];

const LOIO = [
  { index: 'S&P 500',     strat: '+9.82%', bench: '+7.54%', alpha: '+2.28%' },
  { index: 'NASDAQ-100',  strat: '+13.41%', bench: '+11.02%', alpha: '+2.39%' },
  { index: 'Russell 2000', strat: '+8.15%', bench: '+6.18%', alpha: '+1.97%' },
  { index: 'MSCI EAFE',   strat: '+6.73%', bench: '+4.35%', alpha: '+2.38%' },
  { index: 'MSCI EM',     strat: '+7.24%', bench: '+4.89%', alpha: '+2.35%' },
  { index: 'FTSE 100',    strat: '+5.91%', bench: '+3.72%', alpha: '+2.19%' },
  { index: 'DAX',         strat: '+8.56%', bench: '+6.21%', alpha: '+2.35%' },
  { index: 'Nikkei 225',  strat: '+7.88%', bench: '+5.53%', alpha: '+2.35%' },
  { index: 'ASX 200',     strat: '+7.12%', bench: '+5.44%', alpha: '+1.68%' },
];

const SUMMARY = [
  { test: 'Parameter Sensitivity (8 params)', result: '8 / 8 pass', status: 'Pass' },
  { test: 'Neighborhood Robustness (+/-1 step)', result: '50 / 50 pass (100%)', status: 'Pass' },
  { test: 'Time-Period Stability (3 eras)', result: '3 / 3 periods positive alpha', status: 'Pass' },
  { test: 'Leave-One-Index-Out CV', result: '9 / 9 beat benchmark', status: 'Pass' },
  { test: 'Overall Verdict', result: 'ROBUST', status: 'Pass' },
];

const TH = 'text-right py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]';
const TD = 'text-right py-1.5 tabular-nums text-foreground';

export default function RobustnessTab() {
  return (
    <div className="space-y-6">
      <p className="text-[13px] text-muted-foreground leading-relaxed">
        Parameter sensitivity, neighborhood stability, time-period splits, and leave-one-index-out cross-validation.
      </p>

      {/* Verdict Scorecard */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Sensitivity', value: '8 / 8 pass', color: 'text-emerald-500' },
          { label: 'Neighborhood', value: '100%', color: 'text-emerald-500' },
          { label: 'LOIO CV', value: '9 / 9 pass', color: 'text-emerald-500' },
          { label: 'Verdict', value: 'ROBUST', color: 'text-emerald-500' },
        ].map(m => (
          <div key={m.label} className="panel-card px-3 py-2.5 text-center">
            <div className="stat-label mb-1">{m.label}</div>
            <div className={`text-[16px] font-semibold font-mono ${m.color}`}>{m.value}</div>
          </div>
        ))}
      </div>

      {/* Parameter Sensitivity */}
      <div className="panel-card p-4">
        <SectionTitle info="Each parameter varied individually while holding others at defaults">Parameter Sensitivity</SectionTitle>
        <p className="text-[12.5px] text-muted-foreground mb-3">
          All 8 parameters pass (alpha &gt; 0 in &ge;80% of settings).
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Parameter</th>
                <th className={TH}>Result</th>
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Detail</th>
              </tr>
            </thead>
            <tbody>
              {SENSITIVITY_PARAMS.map(p => (
                <tr key={p.param} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground font-medium">{p.param}</td>
                  <td className="text-right py-1.5 text-emerald-500 font-semibold">{p.result}</td>
                  <td className="py-1.5 text-muted-foreground">{p.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Neighborhood Robustness */}
      <div className="panel-card p-4">
        <SectionTitle info="50 random perturbations within +/-1 step of default parameters">Neighborhood Robustness</SectionTitle>
        <p className="text-[12.5px] text-muted-foreground mb-3">
          All 50 produce positive alpha.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Metric</th>
                <th className={TH}>Value</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Mean Neighborhood Score', NEIGHBORHOOD.mean_score],
                ['Min Neighborhood Score', NEIGHBORHOOD.min_score],
                ['Configs Tested', NEIGHBORHOOD.configs_tested],
                ['Configs with alpha > 0', NEIGHBORHOOD.configs_positive],
              ].map(([k, v]) => (
                <tr key={k} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground">{k}</td>
                  <td className={TD}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Time-Period Stability */}
      <div className="panel-card p-4">
        <SectionTitle info="Strategy tested across three non-overlapping sub-periods">Time-Period Stability</SectionTitle>
        <p className="text-[12.5px] text-muted-foreground mb-3">
          Alpha is not concentrated in a single era.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Period</th>
                <th className={TH}>Avg Alpha</th>
                <th className={TH}>Indices Positive</th>
                <th className={TH}>Avg Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {PERIOD_STABILITY.map(p => (
                <tr key={p.period} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground font-medium">{p.period}</td>
                  <td className="text-right py-1.5 tabular-nums text-emerald-500">{p.avg_alpha}</td>
                  <td className={TD}>{p.indices_positive}</td>
                  <td className={TD}>{p.avg_sharpe}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* LOIO Cross-Validation */}
      <div className="panel-card p-4">
        <SectionTitle info="Factor weights trained on 8 indices, tested on held-out 9th">Leave-One-Index-Out Cross-Validation</SectionTitle>
        <p className="text-[12.5px] text-muted-foreground mb-3">
          All 9 held-out indices beat the 50/50 benchmark.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Held-Out Index</th>
                <th className={TH}>Strategy CAGR</th>
                <th className={TH}>Benchmark CAGR</th>
                <th className={TH}>Alpha</th>
              </tr>
            </thead>
            <tbody>
              {LOIO.map(r => (
                <tr key={r.index} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground font-medium">{r.index}</td>
                  <td className={TD}>{r.strat}</td>
                  <td className="text-right py-1.5 tabular-nums text-muted-foreground">{r.bench}</td>
                  <td className="text-right py-1.5 tabular-nums text-emerald-500 font-semibold">{r.alpha}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11.5px] text-muted-foreground/50 mt-2">Average held-out alpha: <span className="text-emerald-500 font-semibold">+2.31%</span> across all 9 indices.</p>
      </div>

      {/* Summary Scorecard */}
      <div className="panel-card p-4">
        <SectionTitle>Summary Scorecard</SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px] font-mono">
            <thead>
              <tr className="border-b border-border/20">
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Test</th>
                <th className="text-left py-1.5 text-muted-foreground/50 font-semibold uppercase tracking-wider text-[11px]">Result</th>
                <th className={TH}>Status</th>
              </tr>
            </thead>
            <tbody>
              {SUMMARY.map(s => (
                <tr key={s.test} className="border-b border-border/10">
                  <td className="py-1.5 text-foreground">{s.test}</td>
                  <td className="py-1.5 text-muted-foreground">{s.result}</td>
                  <td className="text-right py-1.5 text-emerald-500 font-semibold">{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 px-3 py-2 rounded-[var(--radius)] bg-success/5 border border-success/20">
          <p className="text-[12.5px] text-success font-medium">
            Verdict: ROBUST — The strategy survives all four robustness tests.
            Alpha is not an artifact of parameter tuning, time-period selection, or index-specific overfitting.
          </p>
        </div>
      </div>
    </div>
  );
}
