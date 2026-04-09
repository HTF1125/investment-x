"""Registry of all parameterized family strategy instances.

Generates 191 production Strategy objects across 22 families.
"""

from __future__ import annotations
from typing import Any

from ix.core.backtesting.batch.constants import (
    ASSET_CODES, SECTORS, MULTI5, MULTI8, BROAD6,
)
from .static import StaticAllocation
from .momentum import MomentumStrategy, Momentum13612W, SectorMomentum
from .trend import TrendSMA, DualSMA, TrendBreadth
from .dual_momentum import DualMomentum, DefensiveRotation
from .risk_parity import InverseVol, VolTarget
from .macro import MacroLevel, MacroDirection, VixRegime
from .mean_reversion import MeanReversionStrategy
from .seasonal import SeasonalStrategy
from .ensemble import MomentumTrend, MacroTrendEnsemble, TripleSignal, MultiAssetTrendMom
from .risk_control import DrawdownControl, BondRotation, RelativeValue
from .advanced import MultiTimeframe, CompositeMacro, VolScaledMomentum, AdaptiveMomentum, TrendVolFilter
from .rotation import CoreSatellite, RiskOnRiskOff, CrossAssetRotation, EquityRotation, CanaryStrategy


def build_family_specs(
    available_assets: set[str] | None = None,
) -> list[tuple[str, type, dict]]:
    """Return (id, class, kwargs) tuples for all 191 strategies.

    Use ``build_family_registry()`` to eagerly instantiate them.
    """
    specs: list[tuple[str, type, dict]] = []
    avail = available_assets or set(ASSET_CODES.keys())

    def has(*assets):
        return all(a in avail for a in assets)

    # ── STATIC (8) ──────────────────────────────────────────────
    if has("SPY"):
        specs.append(("STATIC_100_SPY", StaticAllocation, {"weights": {"SPY": 1.0}, "name": "100% SPY (Buy & Hold)"}))
    if has("SPY", "IEF"):
        specs.append(("STATIC_50_50", StaticAllocation, {"weights": {"SPY": 0.5, "IEF": 0.5}, "name": "50/50 SPY/IEF"}))
    if has("SPY", "AGG"):
        specs.append(("STATIC_60_40", StaticAllocation, {"weights": {"SPY": 0.6, "AGG": 0.4}, "name": "60/40 SPY/AGG"}))
    if has("SPY", "TLT", "IEI", "GLD", "DBC"):
        specs.append(("STATIC_ALLWEATHER", StaticAllocation, {"weights": {"SPY": 0.30, "TLT": 0.40, "IEI": 0.15, "GLD": 0.075, "DBC": 0.075}, "name": "All Weather"}))
    if has("SPY", "IWM", "TLT", "IEI", "GLD"):
        specs.append(("STATIC_GOLDEN", StaticAllocation, {"weights": {"SPY": 0.20, "IWM": 0.20, "TLT": 0.20, "IEI": 0.20, "GLD": 0.20}, "name": "Golden Butterfly"}))
    if has("SPY", "TLT", "GLD", "BIL"):
        specs.append(("STATIC_PERMANENT", StaticAllocation, {"weights": {"SPY": 0.25, "TLT": 0.25, "GLD": 0.25, "BIL": 0.25}, "name": "Permanent Portfolio"}))
    if has("SPY", "EFA", "AGG"):
        specs.append(("STATIC_3FUND", StaticAllocation, {"weights": {"SPY": 0.34, "EFA": 0.33, "AGG": 0.33}, "name": "Three Fund Portfolio"}))
    if has("SPY", "TLT"):
        specs.append(("STATIC_RISK_PARITY", StaticAllocation, {"weights": {"SPY": 0.35, "TLT": 0.65}, "name": "Static Risk Parity (SPY/TLT)"}))

    # ── MOMENTUM (19) ───────────────────────────────────────────
    if has("SPY", "IEF"):
        for lb in [1, 3, 6, 9, 12]:
            specs.append((f"MOM_{lb}m_US", MomentumStrategy, {"lookback": lb, "assets": ["SPY", "IEF"]}))
    if has("SPY", "EFA", "EEM", "TLT", "GLD"):
        for lb in [3, 6, 12]:
            specs.append((f"MOM_{lb}m_MULTI5", MomentumStrategy, {"lookback": lb, "top_n": 2, "assets": MULTI5}))
    if has("SPY", "IEF"):
        specs.append(("MOM_13612W_US", Momentum13612W, {"assets": ["SPY", "IEF"]}))
    if has("SPY", "EFA", "EEM", "TLT", "GLD", "BIL"):
        specs.append(("MOM_13612W_MULTI5_BIL", Momentum13612W, {"assets": MULTI5, "top_n": 2, "cash": "BIL"}))
    if all(a in avail for a in MULTI8 + ["BIL"]):
        for lb in [6, 12]:
            specs.append((f"MOM_{lb}m_MULTI8_BIL", MomentumStrategy, {"lookback": lb, "top_n": 3, "assets": MULTI8, "cash": "BIL"}))
    if has("SPY") and sum(1 for s in SECTORS if s in avail) >= 5:
        active_sectors = [s for s in SECTORS if s in avail]
        for lb, tn in [(3, 3), (6, 3), (6, 5), (12, 3), (12, 5)]:
            specs.append((f"SECMOM_{lb}m_T{tn}", SectorMomentum, {"lookback": lb, "top_n": tn, "sectors": active_sectors}))
    if has("QQQ", "IEF"):
        for lb in [6, 12]:
            specs.append((f"MOM_{lb}m_QQQ", MomentumStrategy, {"lookback": lb, "assets": ["QQQ", "IEF"]}))

    # ── TREND (19) ──────────────────────────────────────────────
    if has("SPY", "IEF"):
        for sma in [3, 5, 6, 8, 10, 12]:
            specs.append((f"TREND_{sma}m_SPY_IEF", TrendSMA, {"sma_months": sma}))
    if has("SPY", "TLT"):
        for sma in [5, 10, 12]:
            specs.append((f"TREND_{sma}m_SPY_TLT", TrendSMA, {"sma_months": sma, "bond": "TLT"}))
    if has("SPY", "IEF"):
        for fast, slow in [(3, 10), (4, 12), (5, 12), (3, 8)]:
            specs.append((f"DSMA_{fast}_{slow}_SPY_IEF", DualSMA, {"fast": fast, "slow": slow}))
    if all(a in avail for a in MULTI5):
        specs.append(("TBREADTH_MULTI5", TrendBreadth, {"assets": MULTI5}))
    if all(a in avail for a in BROAD6):
        specs.append(("TBREADTH_BROAD6", TrendBreadth, {"assets": BROAD6}))
    if has("QQQ", "IEF"):
        for sma in [8, 10]:
            specs.append((f"TREND_{sma}m_QQQ_IEF", TrendSMA, {"sma_months": sma, "equity": "QQQ"}))
    if has("SPY", "AGG"):
        for sma in [8, 10]:
            specs.append((f"TREND_{sma}m_SPY_AGG", TrendSMA, {"sma_months": sma, "bond": "AGG"}))

    # ── DUAL MOMENTUM (9) ──────────────────────────────────────
    if has("SPY", "EFA", "IEF", "BIL"):
        for lb in [3, 6, 12]:
            specs.append((f"DM_{lb}m_US_INTL", DualMomentum, {"lookback": lb, "risky": ["SPY", "EFA"]}))
    if has("SPY", "EFA", "EEM", "AGG", "BIL"):
        for lb in [6, 12]:
            specs.append((f"DM_{lb}m_GLOBAL", DualMomentum, {"lookback": lb, "risky": ["SPY", "EFA", "EEM"], "safe": "AGG"}))
    if has("TLT", "GLD", "DBC", "BIL", "SPY"):
        for tn in [1, 2, 3]:
            specs.append((f"DEFROT_T{tn}", DefensiveRotation, {"assets": ["TLT", "GLD", "DBC"], "top_n": tn}))
    if has("TLT", "GLD", "DBC", "VNQ", "BIL", "SPY"):
        specs.append(("DEFROT_4A_T2", DefensiveRotation, {"assets": ["TLT", "GLD", "DBC", "VNQ"], "top_n": 2}))

    # ── RISK PARITY (9) ────────────────────────────────────────
    if has("SPY", "IEF"):
        for vw in [6, 12, 24]:
            specs.append((f"IVOL_{vw}m_2A", InverseVol, {"vol_window": vw, "assets": ["SPY", "IEF"]}))
    if all(a in avail for a in MULTI5):
        for vw in [6, 12]:
            specs.append((f"IVOL_{vw}m_5A", InverseVol, {"vol_window": vw, "assets": MULTI5}))
    if all(a in avail for a in BROAD6):
        specs.append(("IVOL_12m_6A", InverseVol, {"vol_window": 12, "assets": BROAD6}))
    if has("SPY", "IEF"):
        for tv in [0.08, 0.12, 0.15]:
            specs.append((f"VTGT_{int(tv*100)}pct", VolTarget, {"target_vol": tv}))

    # ── MACRO (12) ─────────────────────────────────────────────
    if has("SPY", "IEF"):
        for thresh in [48, 50, 52]:
            specs.append((f"MACRO_ISM_LVL_{thresh}", MacroLevel, {"macro_code": "ISM_PMI", "threshold": thresh}))
        for ma in [1, 3, 6]:
            specs.append((f"MACRO_ISM_DIR_{ma}m", MacroDirection, {"macro_code": "ISM_PMI", "ma_window": ma}))
        for ma in [1, 3, 6]:
            specs.append((f"MACRO_CLI_DIR_{ma}m", MacroDirection, {"macro_code": "OECD_CLI", "lag": 2, "ma_window": ma}))
        for hi, lo in [(25, 15), (30, 18), (20, 12)]:
            specs.append((f"MACRO_VIX_{hi}_{lo}", VixRegime, {"high_thresh": hi, "low_thresh": lo}))

    # ── MEAN REVERSION (8) ─────────────────────────────────────
    if has("SPY", "IEF"):
        for period in [5, 9, 14]:
            specs.append((f"RSI_{period}m_SPY", MeanReversionStrategy, {"method": "rsi", "period": period}))
        specs.append(("RSI_9m_TIGHT", MeanReversionStrategy, {"method": "rsi", "period": 9, "overbought": 75, "oversold": 25}))
        for window in [6, 12, 24]:
            specs.append((f"ZSCORE_{window}m_SPY", MeanReversionStrategy, {"method": "zscore", "window": window}))
        specs.append(("ZSCORE_12m_T1", MeanReversionStrategy, {"method": "zscore", "window": 12, "threshold": 1.0}))

    # ── SEASONAL (5) ───────────────────────────────────────────
    if has("SPY", "IEF"):
        specs.append(("SEASON_SELL_MAY", SeasonalStrategy, {"equity_months": [11, 12, 1, 2, 3, 4], "name": "Sell in May"}))
        specs.append(("SEASON_BEST6", SeasonalStrategy, {"equity_months": [10, 11, 12, 1, 2, 3], "name": "Best 6 Months"}))
        specs.append(("SEASON_Q4Q1", SeasonalStrategy, {"equity_months": [10, 11, 12, 1, 2, 3, 4], "name": "Q4/Q1 Effect"}))
        specs.append(("SEASON_WINTER", SeasonalStrategy, {"equity_months": [11, 12, 1], "name": "Winter Rally"}))
        specs.append(("SEASON_SUMMER_AVOID", SeasonalStrategy, {"equity_months": [1, 2, 3, 4, 5, 9, 10, 11, 12], "name": "Summer Avoidance"}))

    # ── ENSEMBLE (16) ──────────────────────────────────────────
    if has("SPY", "IEF"):
        for mode in ["both", "any", "average"]:
            specs.append((f"ENS_MOMTREND_{mode.upper()}", MomentumTrend, {"mom_lookback": 12, "sma_lookback": 10, "mode": mode}))
        for mlb, slb in [(6, 6), (6, 10), (9, 8), (3, 5)]:
            specs.append((f"ENS_MT_{mlb}_{slb}", MomentumTrend, {"mom_lookback": mlb, "sma_lookback": slb}))
        for slb in [8, 10, 12]:
            specs.append((f"ENS_ISMTREND_{slb}", MacroTrendEnsemble, {"sma_lookback": slb}))
        for mlb, slb in [(12, 10), (6, 8), (9, 10)]:
            specs.append((f"ENS_TRIPLE_{mlb}_{slb}", TripleSignal, {"mom_lookback": mlb, "sma_lookback": slb}))
    if all(a in avail for a in MULTI5 + ["BIL"]):
        for sma, mom in [(10, 6), (8, 3), (12, 12)]:
            specs.append((f"ENS_MTMOM_{sma}_{mom}", MultiAssetTrendMom, {"sma_months": sma, "mom_months": mom}))

    # ── DRAWDOWN CONTROL (6) ───────────────────────────────────
    if has("SPY", "IEF"):
        for dd_t in [-0.05, -0.10, -0.15]:
            specs.append((f"DDCTRL_{abs(int(dd_t*100))}pct_12m", DrawdownControl, {"dd_thresh": dd_t, "lookback": 12}))
        for dd_t in [-0.10, -0.15, -0.20]:
            specs.append((f"DDCTRL_{abs(int(dd_t*100))}pct_24m", DrawdownControl, {"dd_thresh": dd_t, "lookback": 24}))

    # ── BOND ROTATION (6) ──────────────────────────────────────
    bond3 = ["TLT", "IEF", "TIP"]
    bond5 = ["TLT", "IEF", "IEI", "TIP", "HYG"]
    if sum(1 for b in bond3 if b in avail) >= 3:
        for lb in [3, 6, 12]:
            specs.append((f"BONDROT_{lb}m_3B", BondRotation, {"lookback": lb, "bonds": bond3}))
    if sum(1 for b in bond5 if b in avail) >= 4:
        for lb in [3, 6, 12]:
            specs.append((f"BONDROT_{lb}m_5B", BondRotation, {"lookback": lb, "bonds": bond5, "top_n": 2}))

    # ── RELATIVE VALUE (8) ─────────────────────────────────────
    if has("SPY", "EFA"):
        for lb in [3, 6, 12]:
            specs.append((f"RV_SPY_EFA_{lb}m", RelativeValue, {"lookback": lb, "asset_a": "SPY", "asset_b": "EFA"}))
    if has("QQQ", "IWM"):
        for lb in [6, 12]:
            specs.append((f"RV_QQQ_IWM_{lb}m", RelativeValue, {"lookback": lb, "asset_a": "QQQ", "asset_b": "IWM"}))
    if has("SPY", "GLD"):
        for lb in [6, 12]:
            specs.append((f"RV_SPY_GLD_{lb}m", RelativeValue, {"lookback": lb, "asset_a": "SPY", "asset_b": "GLD"}))
    if has("SPY", "TLT"):
        specs.append(("RV_SPY_TLT_12m", RelativeValue, {"lookback": 12, "asset_a": "SPY", "asset_b": "TLT"}))

    # ── MULTI-TIMEFRAME (6) ────────────────────────────────────
    if has("SPY", "IEF"):
        for slb, llb, sw in [(1, 12, 0.3), (3, 12, 0.4), (3, 9, 0.5), (1, 6, 0.3), (2, 10, 0.4), (6, 12, 0.5)]:
            specs.append((f"MTF_{slb}_{llb}_w{int(sw*10)}", MultiTimeframe, {"short_lb": slb, "long_lb": llb, "short_weight": sw}))

    # ── COMPOSITE MACRO (5) ────────────────────────────────────
    if has("SPY", "IEF"):
        specs.append(("CMACRO_ISM_CLI", CompositeMacro, {"indicators": [("ISM_PMI", 50, 1, 1.0), ("OECD_CLI", 100, 2, 1.0)]}))
        specs.append(("CMACRO_ISM_VIX", CompositeMacro, {"indicators": [("ISM_PMI", 50, 1, 1.0), ("VIX", 20, 0, 1.0)]}))
        specs.append(("CMACRO_TRIPLE", CompositeMacro, {"indicators": [("ISM_PMI", 50, 1, 1.0), ("OECD_CLI", 100, 2, 1.0), ("VIX", 20, 0, 0.5)]}))
        specs.append(("CMACRO_TRIPLE_HEAVY_ISM", CompositeMacro, {"indicators": [("ISM_PMI", 50, 1, 2.0), ("OECD_CLI", 100, 2, 1.0), ("VIX", 20, 0, 0.5)]}))
        specs.append(("CMACRO_TRIPLE_STRICT", CompositeMacro, {"indicators": [("ISM_PMI", 52, 1, 1.0), ("OECD_CLI", 100.5, 2, 1.0), ("VIX", 22, 0, 1.0)]}))

    # ── VOL-SCALED (6) ─────────────────────────────────────────
    if all(a in avail for a in MULTI5 + ["BIL"]):
        for lb, vw in [(6, 6), (12, 6), (6, 12), (12, 12)]:
            specs.append((f"VSMOM_{lb}m_v{vw}_5A", VolScaledMomentum, {"lookback": lb, "vol_window": vw, "assets": MULTI5, "cash": "BIL"}))
    if all(a in avail for a in MULTI8 + ["BIL"]):
        for lb in [6, 12]:
            specs.append((f"VSMOM_{lb}m_v6_8A", VolScaledMomentum, {"lookback": lb, "vol_window": 6, "assets": MULTI8, "top_n": 3, "cash": "BIL"}))

    # ── ADAPTIVE (6) ───────────────────────────────────────────
    if has("SPY", "IEF"):
        for slb, llb, vt in [(3, 12, 0.18), (3, 12, 0.22), (1, 12, 0.20), (3, 9, 0.18), (6, 12, 0.20), (3, 12, 0.15)]:
            specs.append((f"ADAPT_{slb}_{llb}_v{int(vt*100)}", AdaptiveMomentum, {"short_lb": slb, "long_lb": llb, "vol_threshold": vt}))

    # ── TREND + VOL (6) ────────────────────────────────────────
    if has("SPY", "IEF"):
        for sma, vc in [(8, 0.18), (8, 0.22), (10, 0.18), (10, 0.22), (10, 0.25), (12, 0.20)]:
            specs.append((f"TVF_{sma}m_v{int(vc*100)}", TrendVolFilter, {"sma_months": sma, "vol_cap": vc}))

    # ── CORE-SATELLITE (8) ─────────────────────────────────────
    if has("SPY", "EFA", "EEM", "GLD", "TLT"):
        for cw, lb in [(0.6, 6), (0.6, 12), (0.5, 6), (0.7, 6)]:
            specs.append((f"CS_{int(cw*100)}core_{lb}m", CoreSatellite, {"core_weight": cw, "core": {"SPY": 1.0}, "satellite": ["EFA", "EEM", "GLD", "TLT"], "lookback": lb, "top_n": 2}))
    if has("SPY", "AGG") and sum(1 for s in SECTORS if s in avail) >= 5:
        active_sectors = [s for s in SECTORS if s in avail]
        for lb in [3, 6]:
            specs.append((f"CS_6040_SEC_{lb}m", CoreSatellite, {"core_weight": 0.7, "core": {"SPY": 0.6, "AGG": 0.4}, "satellite": active_sectors, "lookback": lb, "top_n": 3}))
    if all(a in avail for a in ["SPY", "AGG", "QQQ", "IWM", "EFA", "GLD", "DBC", "TLT"]):
        for cw in [0.5, 0.6]:
            specs.append((f"CS_BAL_{int(cw*100)}_BROAD", CoreSatellite, {"core_weight": cw, "core": {"SPY": 0.6, "AGG": 0.4}, "satellite": ["QQQ", "IWM", "EFA", "GLD", "DBC", "TLT"], "lookback": 6, "top_n": 2}))

    # ── RISK-ON/OFF (8) ────────────────────────────────────────
    if has("SPY", "IEF"):
        specs.append(("RORO_2SIG_TM", RiskOnRiskOff, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12})]}))
        specs.append(("RORO_3SIG_TMD", RiskOnRiskOff, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("drawdown", {"lb": 12, "thresh": -0.10})]}))
        specs.append(("RORO_3SIG_TMD_STRICT", RiskOnRiskOff, {"signals": [("trend", {"sma": 8}), ("momentum", {"lb": 6}), ("drawdown", {"lb": 12, "thresh": -0.05})], "threshold": 0.67}))
        specs.append(("RORO_2SIG_FAST", RiskOnRiskOff, {"signals": [("trend", {"sma": 5}), ("momentum", {"lb": 6})]}))
        specs.append(("RORO_4SIG_TMDM", RiskOnRiskOff, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("drawdown", {"lb": 12, "thresh": -0.10}), ("macro", {"macro_code": "ISM_PMI", "thresh": 50, "lag": 1})]}))
        specs.append(("RORO_4SIG_STRICT", RiskOnRiskOff, {"signals": [("trend", {"sma": 8}), ("momentum", {"lb": 9}), ("drawdown", {"lb": 12, "thresh": -0.08}), ("macro", {"macro_code": "ISM_PMI", "thresh": 50, "lag": 1})], "threshold": 0.75}))
        specs.append(("RORO_3SIG_TMC", RiskOnRiskOff, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("macro", {"macro_code": "OECD_CLI", "thresh": 100, "lag": 2})]}))
        specs.append(("RORO_3SIG_TMC_FAST", RiskOnRiskOff, {"signals": [("trend", {"sma": 6}), ("momentum", {"lb": 6}), ("macro", {"macro_code": "OECD_CLI", "thresh": 100, "lag": 2})]}))

    # ── CROSS-ASSET ROTATION (8) ───────────────────────────────
    all_rotate = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC"]
    if sum(1 for a in all_rotate if a in avail) >= 5 and has("BIL"):
        active_rotate = [a for a in all_rotate if a in avail]
        for lb, tn in [(6, 2), (6, 3), (12, 2), (12, 3)]:
            specs.append((f"XROT_{lb}m_T{tn}", CrossAssetRotation, {"lookback": lb, "assets": active_rotate, "top_n": tn, "cash": "BIL"}))
        for tn in [2, 3]:
            specs.append((f"XROT_13612W_T{tn}", CrossAssetRotation, {"lookback": 12, "assets": active_rotate, "top_n": tn, "cash": "BIL", "use_13612w": True}))
    if has("SPY", "TLT", "GLD", "BIL"):
        for lb in [6, 12]:
            specs.append((f"XROT_{lb}m_3A", CrossAssetRotation, {"lookback": lb, "assets": ["SPY", "TLT", "GLD"], "top_n": 1, "cash": "BIL"}))

    # ── EQUITY ROTATION (8) ────────────────────────────────────
    eq3 = ["SPY", "QQQ", "IWM"]
    if all(a in avail for a in eq3) and has("IEF"):
        for lb in [3, 6, 12]:
            specs.append((f"EQROT_{lb}m_3E", EquityRotation, {"lookback": lb, "equities": eq3}))
        for lb in [6, 12]:
            specs.append((f"EQROT_{lb}m_SMA10", EquityRotation, {"lookback": lb, "equities": eq3, "sma_filter": 10}))
    eq5 = ["SPY", "QQQ", "IWM", "EFA", "EEM"]
    if all(a in avail for a in eq5) and has("IEF"):
        for lb in [6, 12]:
            specs.append((f"EQROT_{lb}m_5E", EquityRotation, {"lookback": lb, "equities": eq5, "top_n": 2}))
        specs.append(("EQROT_13612W_5E", EquityRotation, {"lookback": 12, "equities": eq5, "top_n": 2, "sma_filter": 10}))

    # ── CANARY (5) ─────────────────────────────────────────────
    if has("SPY", "EFA", "EEM", "QQQ", "IWM", "TLT", "IEF", "GLD", "BIL"):
        specs.append(("CANARY_BAA_BROAD", CanaryStrategy, {"canary": ["SPY", "EFA"], "offensive": ["SPY", "QQQ", "IWM", "EFA", "EEM"], "defensive": ["TLT", "IEF", "GLD", "BIL"]}))
        specs.append(("CANARY_BAA_AGG", CanaryStrategy, {"canary": ["SPY", "EFA"], "offensive": ["SPY", "QQQ", "IWM", "EFA", "EEM"], "defensive": ["TLT", "IEF", "GLD", "BIL"], "off_top_n": 1, "def_top_n": 1}))
        specs.append(("CANARY_EEM", CanaryStrategy, {"canary": ["EEM"], "offensive": ["SPY", "QQQ", "EFA"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}))
    if has("SPY", "EFA", "AGG", "TLT", "GLD", "BIL"):
        specs.append(("CANARY_AGG", CanaryStrategy, {"canary": ["AGG", "EFA"], "offensive": ["SPY", "QQQ", "EFA", "EEM"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}))
        specs.append(("CANARY_4C", CanaryStrategy, {"canary": ["SPY", "EFA", "EEM", "AGG"], "offensive": ["SPY", "QQQ", "IWM"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}))

    return specs


def build_family_registry(
    available_assets: set[str] | None = None,
) -> list:
    """Instantiate all family strategies as production Strategy objects."""
    specs = build_family_specs(available_assets)
    strategies = []
    for sid, cls, kwargs in specs:
        try:
            s = cls(**kwargs)
            strategies.append(s)
        except Exception:
            pass  # Skip if assets unavailable
    return strategies
