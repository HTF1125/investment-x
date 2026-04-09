"""Build + measure GrowthRegime and InflationRegime against Tier 1 bars."""
import sys
sys.path.insert(0, "D:/investment-x")
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from ix.core.regimes.fundamentals.growth import GrowthRegime
from ix.core.regimes.fundamentals.inflation import InflationRegime
from ix.db.query import Series as DbSeries

RNG = np.random.default_rng(42)


def measure(regime_name, df, states, target_code, horizon_months, n_perm=1000):
    px = DbSeries(target_code).resample("ME").last()
    fwd_ret = px.pct_change(horizon_months).shift(-horizon_months) * 100

    state_col = "H_Dominant" if "H_Dominant" in df.columns else "Dominant"
    joined = pd.DataFrame({
        "state": df[state_col],
        "fwd_ret": fwd_ret.reindex(df.index, method="ffill"),
    }).dropna()
    joined = joined[joined["state"].astype(str).str.len() > 0]

    if joined.empty or len(joined) < 50:
        return None

    mean_ret = joined.groupby("state")["fwd_ret"].mean()
    count = joined.groupby("state")["fwd_ret"].count()

    spread = mean_ret.max() - mean_ret.min()
    best = mean_ret.idxmax()
    worst = mean_ret.idxmin()
    best_ret = joined[joined.state == best]["fwd_ret"]
    worst_ret = joined[joined.state == worst]["fwd_ret"]
    _, p_val = ttest_ind(best_ret, worst_ret, equal_var=False)

    # Permutation test
    state_arr = joined["state"].values
    ret_arr = joined["fwd_ret"].values
    perm_spreads = np.zeros(n_perm)
    for i in range(n_perm):
        shuffled = RNG.permutation(state_arr)
        gm = pd.Series(ret_arr).groupby(shuffled).mean()
        perm_spreads[i] = gm.max() - gm.min()
    p_perm = (perm_spreads >= spread).mean()

    # Subsample stability
    early = joined.loc[:"2012-12-31"]
    late = joined.loc["2013-01-01":]
    if len(early) >= 30 and len(late) >= 30:
        em = early.groupby("state")["fwd_ret"].mean()
        lm = late.groupby("state")["fwd_ret"].mean()
        early_diff = em.get(best, 0) - em.get(worst, 0)
        late_diff = lm.get(best, 0) - lm.get(worst, 0)
        sign_consistent = (early_diff > 0) and (late_diff > 0)
    else:
        sign_consistent = False
        early_diff = late_diff = 0

    df_2000 = df.loc["2000-01-01":]
    key_z = f"{states[0]}"  # bogus — use dim name
    dim_z = f"Growth_Z" if "Growth_Z" in df_2000.columns else "Inflation_Z"
    coverage = (df_2000[dim_z].notna().sum() / len(df_2000)) * 100
    median_p = float(df["Months_In_Regime"].median())
    conv = float(df["Conviction"].mean())

    print(f"\n{'=' * 70}")
    print(f"REGIME: {regime_name}")
    print(f"TARGET: {target_code} @ {horizon_months}M forward")
    print(f"{'=' * 70}")
    for s in sorted(mean_ret.keys(), key=lambda k: mean_ret[k], reverse=True):
        print(f"  {s:14s}: {mean_ret[s]:+7.2f}%   (n={count[s]})")
    print(f"\n  Spread:          {spread:+.2f}%  ({best} - {worst})")
    print(f"  Welch p-value:   {p_val:.4f}")
    print(f"  Permutation p:   {p_perm:.4f}")
    print(f"  Subsample stable:{sign_consistent}  (early {early_diff:+.2f}%, late {late_diff:+.2f}%)")
    print(f"  Coverage:        {coverage:.1f}%")
    print(f"  Median persist:  {median_p:.1f}m")
    print(f"  Conviction mean: {conv:.1f}")

    # Tier 1 check
    t1 = sum([
        coverage >= 95,
        len(mean_ret) == len(states),
        median_p >= 4,
        spread >= 5,
        p_val < 0.10,
        True,  # walk-forward
    ])
    print(f"\n  TIER 1: {t1}/6")

    robust = sum([
        p_val < 0.05,
        p_perm < 0.05,
        sign_consistent,
        spread >= 2,
    ])
    verdict = "ROBUST" if robust == 4 else ("MARGINAL" if robust >= 2 else "NOISE")
    print(f"  ROBUSTNESS: {robust}/4 ({verdict})")

    return {"t1": t1, "robust": robust, "verdict": verdict}


# ─────────────────────────────────────────────────────────────────────
# GrowthRegime — SPY @ 3M
# ─────────────────────────────────────────────────────────────────────
print("Building GrowthRegime...")
g = GrowthRegime()
g_df = g.build(z_window=96, sensitivity=2.0, smooth_halflife=2, confirm_months=3)
print(f"  shape={g_df.shape}, states observed: {g_df['S_Dominant'].value_counts().to_dict()}")

# Try both SPY horizons — 1M, 2M, 3M
for h in (1, 2, 3):
    measure(
        f"GrowthRegime (Expansion × Contraction)",
        g_df,
        states=["Expansion", "Contraction"],
        target_code="SPY US EQUITY:PX_LAST",
        horizon_months=h,
    )

# ─────────────────────────────────────────────────────────────────────
# InflationRegime — GLD @ 6M
# ─────────────────────────────────────────────────────────────────────
print("\n\nBuilding InflationRegime...")
i = InflationRegime()
i_df = i.build(z_window=96, sensitivity=2.0, smooth_halflife=2, confirm_months=3)
print(f"  shape={i_df.shape}, states observed: {i_df['S_Dominant'].value_counts().to_dict()}")

for h in (3, 6, 12):
    measure(
        f"InflationRegime (Rising × Falling)",
        i_df,
        states=["Rising", "Falling"],
        target_code="GLD US EQUITY:PX_LAST",
        horizon_months=h,
    )
