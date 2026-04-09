"""Rotation strategy families — core/satellite, risk-on/off, cross-asset, equity, canary."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES, SECTORS, MULTI5, MULTI8, BROAD6
from ix.db.query import Series as DbSeries


def _score_13612w(px: pd.DataFrame, assets: list[str]) -> pd.Series:
    """Compute 13612W composite momentum score for given assets."""
    if len(px) < 13:
        return pd.Series(dtype=float)
    pr = px[assets]
    r1 = pr.iloc[-1] / pr.iloc[-2] - 1
    r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
    r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
    r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
    return 12 * r1 + 4 * r3 + 2 * r6 + r12


class CoreSatellite(FamilyStrategy):
    """Static core allocation plus momentum-rotated satellite sleeve."""
    family = "Rotation"

    def __init__(
        self,
        core_weight: float = 0.6,
        core: dict[str, float] | None = None,
        satellite: list[str] | None = None,
        lookback: int = 6,
        top_n: int = 1,
        name: str = "",
        **kw,
    ):
        self._core_weight = core_weight
        self._core = core or {"SPY": 0.6, "IEF": 0.4}
        self._satellite = satellite or ["EFA", "EEM", "GLD", "DBC"]
        self._lookback = lookback
        self._top_n = top_n

        all_assets = list(set(list(self._core.keys()) + self._satellite))
        # Benchmark is the static core allocation (what you'd hold passively)
        core_total = sum(self._core.values())
        core_bm = {k: v / core_total for k, v in self._core.items()} if core_total > 0 else self._core
        self._build_universe(all_assets, benchmark=core_bm)

        core_desc = ", ".join(f"{k} {v/core_total:.0%}" for k, v in self._core.items()) if core_total > 0 else ", ".join(self._core.keys())
        sat_list = ", ".join(self._satellite)
        self.label = name or f"CoreSatellite {core_weight:.0%} core, Top{top_n}"
        self.description = (
            f"Core-satellite allocation: {core_weight:.0%} in static core ({core_desc}) "
            f"plus {1-core_weight:.0%} rotated among {len(self._satellite)} satellite "
            f"assets ({sat_list}) by {lookback}-month momentum. Holds top {top_n} "
            f"satellite performers with positive returns. If no satellite qualifies, "
            f"core gets the full allocation. Blends passive stability with tactical "
            f"rotation. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        lb = self._lookback
        sat_assets = self._avail(self._satellite)
        sat_weight = 1 - self._core_weight

        # Core allocation (scaled to core_weight)
        core_total = sum(self._core.values())
        core_w = {k: v / core_total * self._core_weight for k, v in self._core.items()}

        # Satellite by momentum
        if len(px) > lb and sat_assets:
            ret = px[sat_assets].iloc[-1] / px[sat_assets].iloc[-lb - 1] - 1
            ret = ret.dropna()
            positive = ret[ret > 0]

            if not positive.empty:
                top = positive.nlargest(min(self._top_n, len(positive)))
                sat_w = {a: sat_weight / len(top) for a in top.index}
            else:
                # No positive satellite -> give satellite weight to core
                core_total_w = sum(core_w.values())
                if core_total_w > 0:
                    scale = 1.0 / core_total_w
                    core_w = {k: v * scale for k, v in core_w.items()}
                sat_w = {}
        else:
            # Not enough data -> give satellite weight to core
            core_total_w = sum(core_w.values())
            if core_total_w > 0:
                scale = 1.0 / core_total_w
                core_w = {k: v * scale for k, v in core_w.items()}
            sat_w = {}

        w = {**core_w, **sat_w}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "core_weight": self._core_weight,
            "core": self._core,
            "satellite": self._satellite,
            "lookback": self._lookback,
            "top_n": self._top_n,
        }


class RiskOnRiskOff(MacroFamilyStrategy):
    """Multi-signal voting system for equity/bond regime switching.

    Signal types: "trend" (SMA), "momentum" (lookback return), "drawdown",
    "macro" (macro indicator level).
    """
    family = "Rotation"

    def __init__(
        self,
        signals: list[tuple[str, dict]] | None = None,
        equity: str = "SPY",
        bond: str = "IEF",
        threshold: float = 0.5,
        name: str = "",
        **kw,
    ):
        self._signals = signals or [
            ("trend", {"sma": 10}),
            ("momentum", {"lb": 12}),
        ]
        self._equity = equity
        self._bond = bond
        self._threshold = threshold
        self._macro_code = None  # disable single-macro resolution in base
        self._build_universe([equity, bond])
        signal_desc = ", ".join(f"{t}({','.join(f'{k}={v}' for k,v in p.items())})" for t, p in self._signals)
        self.label = name or f"RORO {len(self._signals)} signals"
        self.description = (
            f"Multi-signal risk-on/off: counts votes from {len(self._signals)} "
            f"independent signals ({signal_desc}). Each signal is binary (pass/fail). "
            f"If vote fraction >= {threshold:.0%} → 100% {equity}. If <= "
            f"{1-threshold:.0%} → 100% {bond}. Between → 50/50. Majority-rule ensemble "
            f"avoids single-signal whipsaw. Monthly rebalance."
        )
        super().__init__(**kw)

    def initialize(self):
        super().initialize()
        self._macro_data = {}
        for sig_type, params in self._signals:
            if sig_type == "macro":
                macro_code = params.get("macro_code", "")
                if macro_code in MACRO_CODES:
                    self._macro_data[macro_code] = DbSeries(MACRO_CODES[macro_code])

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        eq = self._equity
        votes = []

        for sig_type, params in self._signals:
            if sig_type == "trend":
                sma = params.get("sma", 10)
                if eq in hist.columns and len(hist) >= sma + 1:
                    price = hist[eq].iloc[-1]
                    sma_val = hist[eq].iloc[-sma:].mean()
                    votes.append(price > sma_val)

            elif sig_type == "momentum":
                lb = params.get("lb", 12)
                if eq in hist.columns and len(hist) > lb:
                    ret = hist[eq].iloc[-1] / hist[eq].iloc[-lb - 1] - 1
                    votes.append(ret > 0)

            elif sig_type == "drawdown":
                lb = params.get("lb", 12)
                thresh = params.get("thresh", -0.10)
                if eq in hist.columns and len(hist) > lb:
                    peak = hist[eq].iloc[-lb:].max()
                    dd = hist[eq].iloc[-1] / peak - 1
                    votes.append(dd > thresh)

            elif sig_type == "macro":
                macro_code = params.get("macro_code", "")
                thresh = params.get("thresh", 50.0)
                lag = params.get("lag", 1)
                series = self._macro_data.get(macro_code)
                if series is not None and not series.empty:
                    m = series.loc[:self.d]
                    if len(m) >= lag + 1:
                        val = m.iloc[-(lag + 1)]
                        if pd.notna(val):
                            votes.append(val > thresh)

        if not votes:
            return self._eq_weight([self._equity, self._bond])

        frac = sum(votes) / len(votes)

        if frac >= self._threshold:
            return self._eq_weight([self._equity])
        if frac <= 1 - self._threshold:
            return self._eq_weight([self._bond])
        return self._eq_weight([self._equity, self._bond])

    def get_params(self) -> dict:
        return {
            "signals": self._signals,
            "equity": self._equity,
            "bond": self._bond,
            "threshold": self._threshold,
        }


class CrossAssetRotation(FamilyStrategy):
    """Cross-asset rotation — rank by simple return or 13612W, pick top N."""
    family = "Rotation"

    def __init__(
        self,
        lookback: int = 12,
        assets: list[str] | None = None,
        top_n: int = 2,
        cash: str | None = None,
        use_13612w: bool = False,
        name: str = "",
        **kw,
    ):
        self._lookback = lookback
        self._assets = assets or BROAD6
        self._top_n = top_n
        self._cash = cash
        self._use_13612w = use_13612w

        all_assets = list(self._assets)
        if cash and cash not in all_assets:
            all_assets.append(cash)
        self._build_universe(all_assets)

        asset_list = ", ".join(self._assets)
        scoring = "13612W composite momentum (12*r1 + 4*r3 + 2*r6 + r12)" if use_13612w else f"{lookback}-month total return"
        cash_desc = ", with BIL cash hurdle" if cash else ""
        self.label = name or f"CrossAsset {'13612W' if use_13612w else f'{lookback}m'} Top{top_n}"
        self.description = (
            f"Cross-asset class rotation: ranks {len(self._assets)} diverse asset "
            f"classes ({asset_list}) by {scoring}. Holds top {top_n} in equal weight"
            f"{cash_desc}. Captures cross-market momentum across equities, bonds, "
            f"commodities, and gold. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        assets = self._avail(self._assets)
        cash = self._cash

        min_hist = 13 if self._use_13612w else self._lookback + 1
        if len(px) < min_hist or not assets:
            return self._eq_weight(assets or ["SPY"])

        if self._use_13612w:
            score = _score_13612w(px, assets)
        else:
            score = px[assets].iloc[-1] / px[assets].iloc[-self._lookback - 1] - 1
        score = score.dropna()

        # Cash hurdle
        if cash and cash in px.columns:
            if self._use_13612w and len(px) >= 13:
                cash_score = _score_13612w(px, [cash])
                cash_score = cash_score.iloc[0] if not cash_score.empty else 0
            elif not self._use_13612w and len(px[cash].dropna()) > self._lookback:
                cash_score = px[cash].iloc[-1] / px[cash].iloc[-self._lookback - 1] - 1
            else:
                cash_score = 0
            candidates = score[score > cash_score]
            if candidates.empty:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
        else:
            candidates = score[score > 0]

        if candidates.empty:
            if cash:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
            return self._eq_weight(assets)

        top = candidates.nlargest(min(self._top_n, len(candidates)))
        w = pd.Series(1.0 / len(top), index=top.index)
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "lookback": self._lookback,
            "assets": self._assets,
            "top_n": self._top_n,
            "cash": self._cash,
            "use_13612w": self._use_13612w,
        }


class EquityRotation(FamilyStrategy):
    """Equity rotation with optional SMA filter and bond fallback."""
    family = "Rotation"

    def __init__(
        self,
        lookback: int = 6,
        equities: list[str] | None = None,
        bond: str = "IEF",
        sma_filter: int = 0,
        top_n: int = 1,
        name: str = "",
        **kw,
    ):
        self._lookback = lookback
        self._equities = equities or ["SPY", "QQQ", "IWM", "EFA", "EEM"]
        self._bond = bond
        self._sma_filter = sma_filter
        self._top_n = top_n

        all_assets = list(set(self._equities + [bond]))
        self._build_universe(all_assets, benchmark={"SPY": 1.0})

        eq_list = ", ".join(self._equities)
        sma_desc = f", filtered to only those above their {sma_filter}-month SMA" if sma_filter else ""
        self.label = name or f"EqRotation {lookback}m Top{top_n}"
        self.description = (
            f"US equity sub-rotation: ranks {len(self._equities)} equity ETFs "
            f"({eq_list}) by {lookback}-month return{sma_desc}. Holds top {top_n} "
            f"with positive returns. If no equity qualifies → 100% {bond} as safety "
            f"valve. Targets outperformance within the equity space by concentrating "
            f"in leading styles/sizes. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        lb = self._lookback
        equities = self._avail(self._equities)

        min_hist = max(lb, self._sma_filter) + 1
        if len(px) < min_hist or not equities:
            return self._eq_weight([self._bond])

        # Optional SMA filter: only consider equities above their SMA
        if self._sma_filter > 0:
            above_sma = []
            for eq in equities:
                if eq in px.columns and len(px[eq].dropna()) >= self._sma_filter:
                    price = px[eq].iloc[-1]
                    sma_val = px[eq].iloc[-self._sma_filter:].mean()
                    if price > sma_val:
                        above_sma.append(eq)
            equities = above_sma

        if not equities:
            return self._eq_weight([self._bond])

        ret = px[equities].iloc[-1] / px[equities].iloc[-lb - 1] - 1
        ret = ret.dropna()
        positive = ret[ret > 0]

        if positive.empty:
            return self._eq_weight([self._bond])

        top = positive.nlargest(min(self._top_n, len(positive)))
        w = pd.Series(1.0 / len(top), index=top.index)
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "lookback": self._lookback,
            "equities": self._equities,
            "bond": self._bond,
            "sma_filter": self._sma_filter,
            "top_n": self._top_n,
        }


class CanaryStrategy(FamilyStrategy):
    """Canary-in-the-coalmine: crash detection via canary assets switches
    between offensive and defensive portfolios.

    If ANY canary asset has negative 13612W score, rotate into defensive.
    Otherwise rotate into offensive.
    """
    family = "Rotation"

    def __init__(
        self,
        canary: list[str] | None = None,
        offensive: list[str] | None = None,
        defensive: list[str] | None = None,
        off_top_n: int = 3,
        def_top_n: int = 2,
        name: str = "",
        **kw,
    ):
        self._canary = canary or ["EEM", "AGG"]
        self._offensive = offensive or ["SPY", "QQQ", "IWM", "EFA", "EEM", "VNQ", "GLD", "DBC"]
        self._defensive = defensive or ["IEF", "TLT", "AGG", "LQD", "TIP", "BIL"]
        self._off_top_n = off_top_n
        self._def_top_n = def_top_n

        all_assets = list(set(self._canary + self._offensive + self._defensive))
        self._build_universe(all_assets, benchmark={"SPY": 0.5, "IEF": 0.5})

        canary_list = ", ".join(self._canary)
        off_list = ", ".join(self._offensive)
        def_list = ", ".join(self._defensive)
        self.label = name or f"Canary Off{off_top_n}/Def{def_top_n}"
        self.description = (
            f"Canary crash detection (Keller BAA): monitors {len(self._canary)} canary "
            f"assets ({canary_list}) using 13612W momentum. If ANY canary turns "
            f"negative → crash detected → switches to defensive universe ({def_list}), "
            f"ranking by 13612W, top {def_top_n}. If all canaries positive → offensive "
            f"universe ({off_list}), top {off_top_n}. The canary pair acts as an early "
            f"warning system for broad market stress. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        if len(px) < 13:
            return self._eq_weight(self._defensive[:self._def_top_n])

        # Check canary signals
        canary_avail = self._avail(self._canary)
        crash = False
        if canary_avail:
            canary_scores = _score_13612w(px, canary_avail)
            if (canary_scores < 0).any():
                crash = True
        else:
            crash = True  # no canary data -> defensive

        if crash:
            # Defensive rotation
            def_avail = self._avail(self._defensive)
            if not def_avail:
                return self._eq_weight(["BIL"] if "BIL" in self.asset_names else self._defensive[:1])
            scores = _score_13612w(px, def_avail)
            scores = scores.dropna()
            if scores.empty:
                return self._eq_weight(def_avail[:self._def_top_n])
            top = scores.nlargest(min(self._def_top_n, len(scores)))
            w = pd.Series(1.0 / len(top), index=top.index)
            return w.reindex(self.asset_names, fill_value=0.0)
        else:
            # Offensive rotation
            off_avail = self._avail(self._offensive)
            if not off_avail:
                return self._eq_weight(self._offensive[:self._off_top_n])
            scores = _score_13612w(px, off_avail)
            scores = scores.dropna()
            if scores.empty:
                return self._eq_weight(off_avail[:self._off_top_n])
            top = scores.nlargest(min(self._off_top_n, len(scores)))
            w = pd.Series(1.0 / len(top), index=top.index)
            return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "canary": self._canary,
            "offensive": self._offensive,
            "defensive": self._defensive,
            "off_top_n": self._off_top_n,
            "def_top_n": self._def_top_n,
        }
