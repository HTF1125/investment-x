# Macro Regime Strategy -- Parameter Testing Results

Generated: 2026-03-15 17:13 UTC

All indicator directions use **empirical IC sign** (no theory-based sign control).

---


## Phase 1: One-at-a-Time Parameter Sweep

Vary one parameter while holding others at their default values.


### Baseline (Default Parameters)

```
alloc_range=(0.1, 1.0), corr_max=0.6, horizon_key=6m, lookback_years=5, macro_trend_split=(0.6, 0.4), rebal_weeks=8, sma_window=30, soft_zone=(0.25, 0.75), top_n=10
```

| Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR | Hit% |
| --- | --- | --- | --- | --- | --- | --- |
| ACWI | 8.35 | 0.869 | -23.4 | 3.21 | 0.808 | 55.8 |


### Varying: `lookback_years`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | ACWI | 9.52 | 1.034 | -20.5 | 4.21 | 1.086 |
| 7 | ACWI | 10.07 | 1.009 | -22.1 | 4.00 | 1.045 |


### Varying: `top_n`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | ACWI | 8.34 | 0.829 | -26.4 | 3.20 | 0.739 |
| 8 | ACWI | 8.51 | 0.882 | -23.2 | 3.38 | 0.837 |
| 15 | ACWI | 7.46 | 0.754 | -26.0 | 2.33 | 0.564 |


### Varying: `corr_max`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5 | ACWI | 8.01 | 0.820 | -25.2 | 2.88 | 0.705 |
| 0.7 | ACWI | 8.37 | 0.863 | -24.4 | 3.23 | 0.768 |


### Varying: `rebal_weeks`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | 1.321 |
| 13 | ACWI | 8.63 | 0.875 | -21.2 | 3.50 | 0.904 |


### Varying: `horizon_key`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 3m | ACWI | 8.35 | 0.869 | -23.4 | 3.21 | 0.808 |


### Varying: `sma_window`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | ACWI | 8.21 | 0.862 | -23.4 | 3.07 | 0.779 |
| 40 | ACWI | 8.49 | 0.863 | -23.4 | 3.35 | 0.827 |


### Varying: `macro_trend_split`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| (0.5, 0.5) | ACWI | 7.98 | 0.813 | -24.6 | 2.85 | 0.656 |
| (0.7, 0.3) | ACWI | 8.71 | 0.922 | -22.1 | 3.57 | 0.961 |
| (1.0, 0.0) | ACWI | 9.72 | 1.048 | -18.3 | 4.59 | 1.218 |


### Varying: `alloc_range`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| (0.1, 0.9) | ACWI | 7.55 | 0.868 | -21.3 | 2.41 | 0.711 |
| (0.0, 1.0) | ACWI | 8.14 | 0.891 | -22.5 | 3.01 | 0.708 |


### Varying: `soft_zone`

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | IR |
| --- | --- | --- | --- | --- | --- | --- |
| (0.2, 0.8) | ACWI | 8.27 | 0.858 | -23.6 | 3.13 | 0.797 |
| (0.35, 0.65) | ACWI | 8.50 | 0.889 | -23.0 | 3.37 | 0.817 |


## Phase 2: Best Parameter Set

**Top 5 parameter sets by average Sharpe:**

| Rank | Avg Sharpe | Avg Alpha% | Avg MaxDD% | Avg IR | Parameters |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.123 | 4.89 | -16.7 | 1.321 | rebal_weeks=4 |
| 2 | 1.048 | 4.59 | -18.3 | 1.218 | macro_trend_split=(1.0, 0.0) |
| 3 | 1.034 | 4.21 | -20.5 | 1.086 | lookback_years=3 |
| 4 | 1.009 | 4.00 | -22.1 | 1.045 | lookback_years=7 |
| 5 | 0.922 | 3.57 | -22.1 | 0.961 | macro_trend_split=(0.7, 0.3) |

**Selected best:** `alloc_range=(0.1, 1.0), corr_max=0.6, horizon_key=6m, lookback_years=5, macro_trend_split=(0.6, 0.4), rebal_weeks=4, sma_window=30, soft_zone=(0.25, 0.75), top_n=10`


## Phase 3: Robustness Testing (One-at-a-Time Perturbation)

Starting from the best parameter set, perturb one parameter at a time.
If performance degrades gracefully, the parameter set is robust.


### Perturbing: `lookback_years` (best=5)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | ACWI | 10.64 | 1.216 | -12.2 | 5.33 | +0.000 |
| 5 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| 7 | ACWI | 11.07 | 1.186 | -16.6 | 5.01 | +0.063 |


### Perturbing: `top_n` (best=10)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | ACWI | 10.08 | 1.133 | -13.8 | 4.94 | +0.000 |
| 8 | ACWI | 10.04 | 1.113 | -16.6 | 4.91 | +0.000 |
| 10 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| 15 | ACWI | 9.49 | 1.063 | -16.5 | 4.35 | -0.059 |


### Perturbing: `corr_max` (best=0.6)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5 | ACWI | 9.87 | 1.117 | -15.1 | 4.73 | +0.000 |
| 0.6 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| 0.7 | ACWI | 10.18 | 1.147 | -15.7 | 5.04 | +0.024 |


### Perturbing: `rebal_weeks` (best=4)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 4 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| 8 | ACWI | 8.35 | 0.869 | -23.4 | 3.21 | -0.253 |
| 13 | ACWI | 8.63 | 0.875 | -21.2 | 3.50 | -0.247 |


### Perturbing: `horizon_key` (best=6m)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 3m | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | +0.000 |
| 6m | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |


### Perturbing: `sma_window` (best=30)

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | ACWI | 9.65 | 1.080 | -16.7 | 4.51 | +0.000 |
| 30 | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| 40 | ACWI | 8.95 | 0.880 | -27.1 | 3.82 | -0.243 |


### Perturbing: `macro_trend_split` (best=(0.6, 0.4))

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| (0.5, 0.5) | ACWI | 10.18 | 1.152 | -14.6 | 5.04 | +0.000 |
| (0.6, 0.4) | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| (0.7, 0.3) | ACWI | 9.86 | 1.084 | -18.8 | 4.73 | -0.038 |
| (1.0, 0.0) | ACWI | 9.30 | 0.934 | -24.8 | 4.16 | -0.189 |


### Perturbing: `alloc_range` (best=(0.1, 1.0))

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| (0.1, 0.9) | ACWI | 9.02 | 1.115 | -15.3 | 3.89 | +0.000 |
| (0.1, 1.0) | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| (0.0, 1.0) | ACWI | 10.00 | 1.190 | -15.1 | 4.86 | +0.067 |


### Perturbing: `soft_zone` (best=(0.25, 0.75))

| Value | Index | Ann Ret% | Sharpe | MaxDD% | Alpha% | vs Best |
| --- | --- | --- | --- | --- | --- | --- |
| (0.2, 0.8) | ACWI | 10.00 | 1.122 | -16.7 | 4.86 | +0.000 |
| (0.25, 0.75) | ACWI | 10.03 | 1.123 | -16.7 | 4.89 | BEST |
| (0.35, 0.65) | ACWI | 10.04 | 1.116 | -16.9 | 4.90 | -0.007 |


### Robustness Summary

**Parameter sensitivity ranking** (higher = more sensitive, less robust):

| Parameter | Avg |Sharpe Delta| | Assessment |
| --- | --- | --- |
| rebal_weeks | 0.2502 | Sensitive |
| sma_window | 0.1215 | Moderate |
| macro_trend_split | 0.0757 | Moderate |
| alloc_range | 0.0337 | Robust |
| lookback_years | 0.0316 | Robust |
| top_n | 0.0197 | Robust |
| corr_max | 0.0121 | Robust |
| soft_zone | 0.0034 | Robust |
| horizon_key | 0.0000 | Robust |


## Final Recommendation

**Best parameters:**
```
alloc_range=(0.1, 1.0), corr_max=0.6, horizon_key=6m, lookback_years=5, macro_trend_split=(0.6, 0.4), rebal_weeks=4, sma_window=30, soft_zone=(0.25, 0.75), top_n=10
```


---
*Completed in 34.2 minutes.*
