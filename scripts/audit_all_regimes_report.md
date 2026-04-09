# Regime sensitivity audit — all 19 regimes

Walk-forward parameter-sensitivity sweep using `audit_regime_sensitivity`
with a 2^4 = 16-cell grid around each regime's default params.

| # | Regime | Target | H | Verdict | Default | Median | Min | Max | Fragile | Flips | VolNorm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | liquidity | SPY US EQUITY:PX_LAST | 3M | **sensitive** | 8.84% | 7.75% | 6.66% | 8.84% | 8/16 | 0 | 0.60 |
| 2 | dollar_level | EEM US EQUITY:PX_LAST | 6M | **robust** | 6.43% | 6.78% | 6.43% | 7.12% | 0/16 | 0 | 0.31 |
| 3 | dollar_trend | EEM US EQUITY:PX_LAST | 6M | **sensitive** | 5.97% | 5.15% | 0.55% | 11.55% | 8/16 | 0 | 0.29 |
| 4 | credit_level | HYG US EQUITY:PX_LAST | 6M | **robust** | 5.85% | 5.86% | 5.46% | 6.12% | 0/16 | 0 | 0.56 |
| 5 | credit_trend | HYG US EQUITY:PX_LAST | 6M | **robust** | 2.18% | 2.43% | 2.18% | 2.77% | 0/16 | 0 | 0.21 |
| 6 | growth | SPY US EQUITY:PX_LAST | 3M | **robust** | 7.24% | 8.65% | 7.24% | 10.11% | 0/16 | 0 | 0.49 |
| 7 | inflation | CL1 Comdty:PX_LAST | 6M | **sensitive** | 18.21% | 15.53% | 10.66% | 18.40% | 8/16 | 0 | 0.50 |
| 8 | yield_curve | SPY US EQUITY:PX_LAST | 12M | **robust** | 6.00% | 6.38% | 6.00% | 6.91% | 0/16 | 0 | 0.41 |
| 9 | real_rates | GC1 Comdty:PX_LAST | 12M | **sensitive** | 14.02% | 12.71% | 11.20% | 14.07% | 4/16 | 0 | 0.87 |
| 10 | vol_term | SPY US EQUITY:PX_LAST | 3M | **robust** | 8.47% | 9.75% | 8.47% | 11.04% | 0/16 | 0 | 0.54 |
| 11 | breadth | SPY US EQUITY:PX_LAST | 3M | **sensitive** | 6.88% | 6.26% | 4.49% | 6.88% | 4/16 | 0 | 0.49 |
| 12 | earnings_revisions | SPY US EQUITY:PX_LAST | 3M | **sensitive** | 8.21% | 7.50% | 3.43% | 8.79% | 4/16 | 0 | 0.59 |
| 13 | positioning | SPY US EQUITY:PX_LAST | 3M | **robust** | 5.05% | 8.58% | 5.05% | 40.43% | 0/16 | 0 | 0.32 |
| 14 | risk_appetite | SPY US EQUITY:PX_LAST | 3M | **sensitive** | 6.81% | 6.59% | 2.53% | 9.09% | 4/16 | 0 | 0.46 |
| 15 | liquidity_impulse | SPY US EQUITY:PX_LAST | 3M | **robust** | 10.66% | 10.46% | 9.02% | 12.02% | 0/16 | 0 | 0.74 |
| 16 | labor | SPY US EQUITY:PX_LAST | 3M | **robust** | 4.26% | 4.50% | 3.61% | 5.44% | 0/16 | 0 | 0.29 |
| 17 | commodity_cycle | SPY US EQUITY:PX_LAST | 3M | **robust** | 10.46% | 10.28% | 9.89% | 10.53% | 0/16 | 0 | 0.71 |
| 18 | dispersion | SPY US EQUITY:PX_LAST | 3M | **sensitive** | 15.23% | 13.82% | 9.36% | 29.97% | 6/16 | 0 | 1.06 |
| 19 | cb_surprise | SPY US EQUITY:PX_LAST | 1M | **robust** | 15.54% | 20.33% | 15.26% | 25.31% | 0/4 | 0 | 1.06 |

**Fragility verdict scale** — `robust` (≥80% of grid cells ≥80% of default, no sign flips) · `sensitive` (stable sign but ≥20% below 80% of default) · `fragile` (sign flip or median < half default, T1.7 fail).