"""Test InflationRegime against multiple candidate targets."""
import sys
sys.path.insert(0, "D:/investment-x")
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from ix.core.regimes.fundamentals.inflation import InflationRegime
from ix.db.query import Series as DbSeries

RNG = np.random.default_rng(42)

regime = InflationRegime()
df = regime.build(z_window=96, sensitivity=2.0, smooth_halflife=2, confirm_months=3)

state_col = "H_Dominant"


def score(target_code, horizon_months):
    try:
        px = DbSeries(target_code).resample("ME").last()
    except Exception:
        return None
    if px.empty:
        return None
    fwd_ret = px.pct_change(horizon_months).shift(-horizon_months) * 100

    joined = pd.DataFrame({
        "state": df[state_col],
        "fwd_ret": fwd_ret.reindex(df.index, method="ffill"),
    }).dropna()
    joined = joined[joined["state"].astype(str).str.len() > 0]

    if len(joined) < 50:
        return None

    mr = joined.groupby("state")["fwd_ret"].mean()
    spread = mr.max() - mr.min()
    best = mr.idxmax()
    worst = mr.idxmin()
    b = joined[joined.state == best]["fwd_ret"]
    w = joined[joined.state == worst]["fwd_ret"]
    _, p = ttest_ind(b, w, equal_var=False)

    # Permutation
    state_arr = joined["state"].values
    ret_arr = joined["fwd_ret"].values
    perm = np.zeros(500)
    for i in range(500):
        sh = RNG.permutation(state_arr)
        gm = pd.Series(ret_arr).groupby(sh).mean()
        perm[i] = gm.max() - gm.min()
    p_perm = (perm >= spread).mean()

    # Subsample
    early = joined.loc[:"2012-12-31"]
    late = joined.loc["2013-01-01":]
    if len(early) >= 30 and len(late) >= 30:
        em = early.groupby("state")["fwd_ret"].mean()
        lm = late.groupby("state")["fwd_ret"].mean()
        ed = em.get(best, 0) - em.get(worst, 0)
        ld = lm.get(best, 0) - lm.get(worst, 0)
        stable = (ed > 0) and (ld > 0)
    else:
        stable = False

    return {
        "target": target_code,
        "h": horizon_months,
        "spread": spread,
        "best": best,
        "worst": worst,
        "p": p,
        "p_perm": p_perm,
        "stable": stable,
        "n": len(joined),
    }


targets = [
    "GLD US EQUITY:PX_LAST",
    "DBC US EQUITY:PX_LAST",      # Broad commodities
    "TIP US EQUITY:PX_LAST",      # TIPS
    "DBA US EQUITY:PX_LAST",      # Agriculture
    "USO US EQUITY:PX_LAST",      # Oil
    "SLV US EQUITY:PX_LAST",      # Silver
    "CL1 Comdty:PX_LAST",         # WTI futures
    "XLE US EQUITY:PX_LAST",      # Energy equities
]

print(f"{'Target':<30} {'H':<4} {'Spread':<10} {'Best':<10} {'p':<8} {'perm':<8} {'stable':<8} {'verdict'}")
print("-" * 95)
for t in targets:
    for h in (3, 6, 12):
        r = score(t, h)
        if r is None:
            continue
        robust = sum([r['p'] < 0.05, r['p_perm'] < 0.05, r['stable'], r['spread'] >= 2])
        v = "ROBUST" if robust == 4 else ("MARGINAL" if robust >= 2 else "NOISE")
        print(f"{t:<30} {r['h']}M{'':<2} {r['spread']:+6.2f}%{'':<2} {r['best']:<10} {r['p']:.3f}   {r['p_perm']:.3f}   {str(r['stable']):<8} {v}")
