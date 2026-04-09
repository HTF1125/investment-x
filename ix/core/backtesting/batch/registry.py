"""Strategy config registry and batch builder."""

import pandas as pd
from typing import Any
from copy import deepcopy

from ix.db.query import Series as DbSeries
from .constants import ASSET_CODES, MACRO_CODES, SECTORS, MULTI5, MULTI8, BROAD6
from .weight_functions import (
    wf_static, wf_momentum, wf_momentum_13612w, wf_sector_momentum,
    wf_trend_sma, wf_dual_sma, wf_trend_breadth,
    wf_dual_momentum, wf_defensive_rotation,
    wf_inverse_vol, wf_vol_target,
    wf_macro_level, wf_macro_direction, wf_vix_regime,
    wf_rsi, wf_zscore, wf_seasonal,
    wf_mom_trend, wf_macro_trend, wf_triple, wf_multi_trend_momentum,
    wf_drawdown_control, wf_bond_rotation, wf_relative_value,
    wf_multi_timeframe, wf_composite_macro, wf_vol_scaled_momentum,
    wf_adaptive_momentum, wf_core_satellite, wf_roro,
    wf_cross_asset_rotation, wf_trend_vol_filter, wf_equity_rotation,
    wf_canary,
)
from .adapter import BatchStrategy


def _cfg(id: str, name: str, family: str, fn, params: dict, desc: str = "") -> dict:
    return {"id": id, "name": name, "family": family, "fn": fn, "params": params, "desc": desc}


def _build_configs(
    available_assets: set[str] | None = None,
    macro_data: dict[str, Any] | None = None,
) -> list[dict]:
    """Build all strategy configs.

    When called from the Streamlit app, *macro_data* values are live
    ``pd.Series``.  When called from ``build_batch_registry()`` they are
    string placeholders (``"ISM_PMI"``) that ``BatchStrategy.initialize``
    resolves to DB Series at runtime.
    """
    S: list[dict] = []

    if available_assets is None:
        available_assets = set(ASSET_CODES.keys())

    if macro_data is None:
        macro_data = {}

    avail = available_assets

    def has(*assets):
        return all(a in avail for a in assets)

    # ── STATIC BENCHMARKS ────────────────────────────────────────
    if has("SPY"):
        S.append(_cfg("STATIC_100_SPY", "100% SPY (Buy & Hold)", "Static", wf_static, {"weights": {"SPY": 1.0}}, "Full equity exposure"))
    if has("SPY", "IEF"):
        S.append(_cfg("STATIC_50_50", "50/50 SPY/IEF", "Static", wf_static, {"weights": {"SPY": 0.5, "IEF": 0.5}}, "Equal stock/bond"))
    if has("SPY", "AGG"):
        S.append(_cfg("STATIC_60_40", "60/40 SPY/AGG", "Static", wf_static, {"weights": {"SPY": 0.6, "AGG": 0.4}}, "Classic balanced"))
    if has("SPY", "TLT", "IEI", "GLD", "DBC"):
        S.append(_cfg("STATIC_ALLWEATHER", "All Weather", "Static", wf_static, {"weights": {"SPY": 0.30, "TLT": 0.40, "IEI": 0.15, "GLD": 0.075, "DBC": 0.075}}, "Dalio risk parity"))
    if has("SPY", "IWM", "TLT", "IEI", "GLD"):
        S.append(_cfg("STATIC_GOLDEN", "Golden Butterfly", "Static", wf_static, {"weights": {"SPY": 0.20, "IWM": 0.20, "TLT": 0.20, "IEI": 0.20, "GLD": 0.20}}, "20% each 5 assets"))
    if has("SPY", "TLT", "GLD", "BIL"):
        S.append(_cfg("STATIC_PERMANENT", "Permanent Portfolio", "Static", wf_static, {"weights": {"SPY": 0.25, "TLT": 0.25, "GLD": 0.25, "BIL": 0.25}}, "Browne permanent"))
    if has("SPY", "EFA", "AGG"):
        S.append(_cfg("STATIC_3FUND", "Three Fund Portfolio", "Static", wf_static, {"weights": {"SPY": 0.34, "EFA": 0.33, "AGG": 0.33}}, "US/Intl/Bond"))
    if has("SPY", "TLT"):
        S.append(_cfg("STATIC_RISK_PARITY", "Static Risk Parity (SPY/TLT)", "Static", wf_static, {"weights": {"SPY": 0.35, "TLT": 0.65}}, "Vol-balanced S/B"))

    # ── MOMENTUM ─────────────────────────────────────────────────
    if has("SPY", "IEF"):
        for lb in [1, 3, 6, 9, 12]:
            S.append(_cfg(f"MOM_{lb}m_US", f"{lb}M Momentum (SPY/IEF)", "Momentum", wf_momentum, {"lookback": lb, "top_n": 1, "assets": ["SPY", "IEF"]}, f"{lb}-month absolute momentum"))
    if has("SPY", "EFA", "EEM", "TLT", "GLD"):
        for lb in [3, 6, 12]:
            S.append(_cfg(f"MOM_{lb}m_MULTI5", f"{lb}M Momentum (5-Asset)", "Momentum", wf_momentum, {"lookback": lb, "top_n": 2, "assets": MULTI5}, f"{lb}-month momentum, top 2 of 5"))
    if has("SPY", "IEF"):
        S.append(_cfg("MOM_13612W_US", "13612W Momentum (SPY/IEF)", "Momentum", wf_momentum_13612w, {"assets": ["SPY", "IEF"], "top_n": 1}, "Keller weighted momentum"))
    if has("SPY", "EFA", "EEM", "TLT", "GLD", "BIL"):
        S.append(_cfg("MOM_13612W_MULTI5_BIL", "13612W Momentum (5-Asset, BIL Hurdle)", "Momentum", wf_momentum_13612w, {"assets": MULTI5, "top_n": 2, "cash": "BIL"}, "Weighted momentum with cash filter"))
    if all(a in avail for a in MULTI8 + ["BIL"]):
        for lb in [6, 12]:
            S.append(_cfg(f"MOM_{lb}m_MULTI8_BIL", f"{lb}M Momentum (8-Asset, BIL)", "Momentum", wf_momentum, {"lookback": lb, "top_n": 3, "assets": MULTI8, "cash": "BIL"}, f"{lb}-month momentum, top 3 of 8"))
    if has("SPY") and sum(1 for s in SECTORS if s in avail) >= 5:
        active_sectors = [s for s in SECTORS if s in avail]
        for lb, tn in [(3, 3), (6, 3), (6, 5), (12, 3), (12, 5)]:
            S.append(_cfg(f"SECMOM_{lb}m_T{tn}", f"Sector Mom {lb}M Top {tn}", "Momentum", wf_sector_momentum, {"lookback": lb, "top_n": tn, "sectors": active_sectors, "fallback": "SPY"}, f"Sector rotation: top {tn} by {lb}-month return"))
    if has("QQQ", "IEF"):
        for lb in [6, 12]:
            S.append(_cfg(f"MOM_{lb}m_QQQ", f"{lb}M Momentum (QQQ/IEF)", "Momentum", wf_momentum, {"lookback": lb, "top_n": 1, "assets": ["QQQ", "IEF"]}, f"{lb}-month momentum on Nasdaq"))

    # ── TREND ────────────────────────────────────────────────────
    if has("SPY", "IEF"):
        for sma in [3, 5, 6, 8, 10, 12]:
            S.append(_cfg(f"TREND_{sma}m_SPY_IEF", f"{sma}M SMA Trend (SPY/IEF)", "Trend", wf_trend_sma, {"sma_months": sma, "equity": "SPY", "bond": "IEF"}, f"Price vs {sma}-month SMA"))
    if has("SPY", "TLT"):
        for sma in [5, 10, 12]:
            S.append(_cfg(f"TREND_{sma}m_SPY_TLT", f"{sma}M SMA Trend (SPY/TLT)", "Trend", wf_trend_sma, {"sma_months": sma, "equity": "SPY", "bond": "TLT"}, f"Price vs {sma}-month SMA, long bonds"))
    if has("SPY", "IEF"):
        for fast, slow in [(3, 10), (4, 12), (5, 12), (3, 8)]:
            S.append(_cfg(f"DSMA_{fast}_{slow}_SPY_IEF", f"Dual SMA {fast}/{slow} (SPY/IEF)", "Trend", wf_dual_sma, {"fast": fast, "slow": slow, "equity": "SPY", "bond": "IEF"}, f"{fast}-month SMA vs {slow}-month SMA"))
    if all(a in avail for a in MULTI5):
        S.append(_cfg("TBREADTH_MULTI5", "Trend Breadth (5-Asset)", "Trend", wf_trend_breadth, {"sma_months": 10, "assets": MULTI5, "equity": "SPY", "bond": "IEF"}, "% assets above 10M SMA as equity weight"))
    if all(a in avail for a in BROAD6):
        S.append(_cfg("TBREADTH_BROAD6", "Trend Breadth (6-Asset)", "Trend", wf_trend_breadth, {"sma_months": 10, "assets": BROAD6, "equity": "SPY", "bond": "IEF"}, "% of 6 assets above 10M SMA"))
    if has("QQQ", "IEF"):
        for sma in [8, 10]:
            S.append(_cfg(f"TREND_{sma}m_QQQ_IEF", f"{sma}M SMA Trend (QQQ/IEF)", "Trend", wf_trend_sma, {"sma_months": sma, "equity": "QQQ", "bond": "IEF"}, f"Nasdaq trend {sma}M SMA"))
    if has("SPY", "AGG"):
        for sma in [8, 10]:
            S.append(_cfg(f"TREND_{sma}m_SPY_AGG", f"{sma}M SMA Trend (SPY/AGG)", "Trend", wf_trend_sma, {"sma_months": sma, "equity": "SPY", "bond": "AGG"}, f"SPY trend vs Agg bonds"))

    # ── DUAL MOMENTUM ────────────────────────────────────────────
    if has("SPY", "EFA", "IEF", "BIL"):
        for lb in [3, 6, 12]:
            S.append(_cfg(f"DM_{lb}m_US_INTL", f"Dual Mom {lb}M (US/Intl)", "Dual Momentum", wf_dual_momentum, {"lookback": lb, "risky": ["SPY", "EFA"], "safe": "IEF", "cash": "BIL"}, f"Antonacci {lb}M"))
    if has("SPY", "EFA", "EEM", "AGG", "BIL"):
        for lb in [6, 12]:
            S.append(_cfg(f"DM_{lb}m_GLOBAL", f"Dual Mom {lb}M (Global)", "Dual Momentum", wf_dual_momentum, {"lookback": lb, "risky": ["SPY", "EFA", "EEM"], "safe": "AGG", "cash": "BIL"}, f"Global dual momentum {lb}M"))
    if has("TLT", "GLD", "DBC", "BIL", "SPY"):
        for tn in [1, 2, 3]:
            S.append(_cfg(f"DEFROT_T{tn}", f"Defensive Rotation Top {tn}", "Dual Momentum", wf_defensive_rotation, {"assets": ["TLT", "GLD", "DBC"], "cash": "BIL", "top_n": tn, "fallback": "SPY"}, f"Rank defensive assets by 13612W, top {tn}"))
    if has("TLT", "GLD", "DBC", "VNQ", "BIL", "SPY"):
        S.append(_cfg("DEFROT_4A_T2", "Defensive Rotation 4-Asset Top 2", "Dual Momentum", wf_defensive_rotation, {"assets": ["TLT", "GLD", "DBC", "VNQ"], "cash": "BIL", "top_n": 2, "fallback": "SPY"}, "4 defensive assets ranked by 13612W"))

    # ── RISK PARITY ──────────────────────────────────────────────
    if has("SPY", "IEF"):
        for vw in [6, 12, 24]:
            S.append(_cfg(f"IVOL_{vw}m_2A", f"Inverse Vol {vw}M (SPY/IEF)", "Risk Parity", wf_inverse_vol, {"vol_window": vw, "assets": ["SPY", "IEF"]}, f"Inverse volatility with {vw}-month window"))
    if all(a in avail for a in MULTI5):
        for vw in [6, 12]:
            S.append(_cfg(f"IVOL_{vw}m_5A", f"Inverse Vol {vw}M (5-Asset)", "Risk Parity", wf_inverse_vol, {"vol_window": vw, "assets": MULTI5}, f"5-asset inverse vol"))
    if all(a in avail for a in BROAD6):
        S.append(_cfg("IVOL_12m_6A", "Inverse Vol 12M (6-Asset)", "Risk Parity", wf_inverse_vol, {"vol_window": 12, "assets": BROAD6}, "6-asset inverse vol"))
    if has("SPY", "IEF"):
        for tv in [0.08, 0.12, 0.15]:
            S.append(_cfg(f"VTGT_{int(tv*100)}pct", f"Vol Target {int(tv*100)}%", "Risk Parity", wf_vol_target, {"target_vol": tv, "vol_window": 12, "equity": "SPY", "bond": "IEF"}, f"Scale equity to {int(tv*100)}% vol"))

    # ── MACRO ────────────────────────────────────────────────────
    ism = macro_data.get("ISM_PMI")
    cli = macro_data.get("OECD_CLI")
    vix = macro_data.get("VIX")

    if ism is not None and has("SPY", "IEF"):
        for thresh in [48, 50, 52]:
            S.append(_cfg(f"MACRO_ISM_LVL_{thresh}", f"ISM PMI Level > {thresh}", "Macro", wf_macro_level, {"macro_data": ism, "threshold": thresh, "lag": 1, "equity": "SPY", "bond": "IEF"}, f"Risk-on when ISM > {thresh}"))
        for ma in [1, 3, 6]:
            S.append(_cfg(f"MACRO_ISM_DIR_{ma}m", f"ISM PMI Direction ({ma}M MA)", "Macro", wf_macro_direction, {"macro_data": ism, "lag": 1, "ma_window": ma, "equity": "SPY", "bond": "IEF"}, f"Risk-on when ISM {ma}M MA rising"))
    if cli is not None and has("SPY", "IEF"):
        for ma in [1, 3, 6]:
            S.append(_cfg(f"MACRO_CLI_DIR_{ma}m", f"OECD CLI Direction ({ma}M MA)", "Macro", wf_macro_direction, {"macro_data": cli, "lag": 2, "ma_window": ma, "equity": "SPY", "bond": "IEF"}, f"Risk-on when CLI {ma}M MA rising"))
    if vix is not None and has("SPY", "IEF"):
        for hi, lo in [(25, 15), (30, 18), (20, 12)]:
            S.append(_cfg(f"MACRO_VIX_{hi}_{lo}", f"VIX Contrarian {lo}/{hi}", "Macro", wf_vix_regime, {"macro_data": vix, "high_thresh": hi, "low_thresh": lo, "equity": "SPY", "bond": "IEF"}, f"Contrarian: bullish VIX>{hi}, cautious VIX<{lo}"))

    # ── MEAN REVERSION ───────────────────────────────────────────
    if has("SPY", "IEF"):
        for period in [5, 9, 14]:
            S.append(_cfg(f"RSI_{period}m_SPY", f"RSI({period}M) Mean Reversion", "Mean Reversion", wf_rsi, {"period": period, "equity": "SPY", "bond": "IEF", "overbought": 70, "oversold": 30}, f"{period}-month RSI contrarian"))
        S.append(_cfg("RSI_9m_TIGHT", "RSI(9M) Tight (25/75)", "Mean Reversion", wf_rsi, {"period": 9, "equity": "SPY", "bond": "IEF", "overbought": 75, "oversold": 25}, "Tighter RSI thresholds"))
        for window in [6, 12, 24]:
            S.append(_cfg(f"ZSCORE_{window}m_SPY", f"Z-Score({window}M)", "Mean Reversion", wf_zscore, {"window": window, "equity": "SPY", "bond": "IEF", "threshold": 1.5}, f"{window}-month price z-score"))
        S.append(_cfg("ZSCORE_12m_T1", "Z-Score(12M) Thresh=1.0", "Mean Reversion", wf_zscore, {"window": 12, "equity": "SPY", "bond": "IEF", "threshold": 1.0}, "Lower threshold z-score"))

    # ── SEASONAL ─────────────────────────────────────────────────
    if has("SPY", "IEF"):
        S.append(_cfg("SEASON_SELL_MAY", "Sell in May", "Seasonal", wf_seasonal, {"equity_months": [11, 12, 1, 2, 3, 4], "equity": "SPY", "bond": "IEF"}, "Equity Nov-Apr"))
        S.append(_cfg("SEASON_BEST6", "Best 6 Months", "Seasonal", wf_seasonal, {"equity_months": [10, 11, 12, 1, 2, 3], "equity": "SPY", "bond": "IEF"}, "Equity Oct-Mar"))
        S.append(_cfg("SEASON_Q4Q1", "Q4/Q1 Effect", "Seasonal", wf_seasonal, {"equity_months": [10, 11, 12, 1, 2, 3, 4], "equity": "SPY", "bond": "IEF"}, "Equity Oct-Apr"))
        S.append(_cfg("SEASON_WINTER", "Winter Rally", "Seasonal", wf_seasonal, {"equity_months": [11, 12, 1], "equity": "SPY", "bond": "IEF"}, "Equity Nov-Jan only"))
        S.append(_cfg("SEASON_SUMMER_AVOID", "Summer Avoidance", "Seasonal", wf_seasonal, {"equity_months": [1, 2, 3, 4, 5, 9, 10, 11, 12], "equity": "SPY", "bond": "IEF"}, "Avoid Jun-Aug only"))

    # ── ENSEMBLE ─────────────────────────────────────────────────
    if has("SPY", "IEF"):
        for mode in ["both", "any", "average"]:
            S.append(_cfg(f"ENS_MOMTREND_{mode.upper()}", f"Mom+Trend ({mode})", "Ensemble", wf_mom_trend, {"mom_lookback": 12, "sma_lookback": 10, "equity": "SPY", "bond": "IEF", "mode": mode}, f"12M momentum + 10M SMA, {mode} rule"))
        for mlb, slb in [(6, 6), (6, 10), (9, 8), (3, 5)]:
            S.append(_cfg(f"ENS_MT_{mlb}_{slb}", f"Mom({mlb}M)+Trend({slb}M)", "Ensemble", wf_mom_trend, {"mom_lookback": mlb, "sma_lookback": slb, "equity": "SPY", "bond": "IEF", "mode": "both"}, f"{mlb}M momentum + {slb}M SMA, both required"))
    if ism is not None and has("SPY", "IEF"):
        for slb in [8, 10, 12]:
            S.append(_cfg(f"ENS_ISMTREND_{slb}", f"ISM+Trend({slb}M)", "Ensemble", wf_macro_trend, {"macro_data": ism, "threshold": 50, "lag": 1, "sma_lookback": slb, "equity": "SPY", "bond": "IEF"}, f"ISM>50 + price>{slb}M SMA"))
        for mlb, slb in [(12, 10), (6, 8), (9, 10)]:
            S.append(_cfg(f"ENS_TRIPLE_{mlb}_{slb}", f"Triple({mlb}M/{slb}M/ISM)", "Ensemble", wf_triple, {"macro_data": ism, "threshold": 50, "lag": 1, "mom_lookback": mlb, "sma_lookback": slb, "equity": "SPY", "bond": "IEF"}, f"Momentum+Trend+ISM voting"))
    if all(a in avail for a in MULTI5 + ["BIL"]):
        for sma, mom in [(10, 6), (8, 3), (12, 12)]:
            S.append(_cfg(f"ENS_MTMOM_{sma}_{mom}", f"Multi-Asset Trend+Mom ({sma}M/{mom}M)", "Ensemble", wf_multi_trend_momentum, {"sma_months": sma, "mom_months": mom, "assets": MULTI5, "cash": "BIL", "top_n": 2}, f"Rotate top 2 of 5"))

    # ── DRAWDOWN CONTROL ─────────────────────────────────────────
    if has("SPY", "IEF"):
        for dd_t in [-0.05, -0.10, -0.15]:
            S.append(_cfg(f"DDCTRL_{abs(int(dd_t*100))}pct_12m", f"DD Control {int(dd_t*100)}% (12M Peak)", "Drawdown Control", wf_drawdown_control, {"dd_thresh": dd_t, "lookback": 12, "equity": "SPY", "bond": "IEF"}, f"Cut equity when DD from 12M peak > {int(dd_t*100)}%"))
        for dd_t in [-0.10, -0.15, -0.20]:
            S.append(_cfg(f"DDCTRL_{abs(int(dd_t*100))}pct_24m", f"DD Control {int(dd_t*100)}% (24M Peak)", "Drawdown Control", wf_drawdown_control, {"dd_thresh": dd_t, "lookback": 24, "equity": "SPY", "bond": "IEF"}, f"Cut equity when DD from 24M peak > {int(dd_t*100)}%"))

    # ── BOND ROTATION ────────────────────────────────────────────
    bond_universe_3 = ["TLT", "IEF", "TIP"]
    bond_universe_5 = ["TLT", "IEF", "IEI", "TIP", "HYG"]
    if sum(1 for b in bond_universe_3 if b in avail) >= 3:
        for lb in [3, 6, 12]:
            S.append(_cfg(f"BONDROT_{lb}m_3B", f"Bond Rotation {lb}M (3 ETFs)", "Bond Rotation", wf_bond_rotation, {"lookback": lb, "bonds": bond_universe_3, "top_n": 1}, f"Best of TLT/IEF/TIP by {lb}M return"))
    if sum(1 for b in bond_universe_5 if b in avail) >= 4:
        for lb in [3, 6, 12]:
            S.append(_cfg(f"BONDROT_{lb}m_5B", f"Bond Rotation {lb}M (5 ETFs)", "Bond Rotation", wf_bond_rotation, {"lookback": lb, "bonds": bond_universe_5, "top_n": 2}, f"Top 2 of 5 bond ETFs by {lb}M return"))

    # ── RELATIVE VALUE ───────────────────────────────────────────
    if has("SPY", "EFA"):
        for lb in [3, 6, 12]:
            S.append(_cfg(f"RV_SPY_EFA_{lb}m", f"US vs Intl {lb}M", "Relative Value", wf_relative_value, {"lookback": lb, "asset_a": "SPY", "asset_b": "EFA"}, f"Relative momentum: SPY vs EFA {lb}M"))
    if has("QQQ", "IWM"):
        for lb in [6, 12]:
            S.append(_cfg(f"RV_QQQ_IWM_{lb}m", f"Growth vs Value {lb}M", "Relative Value", wf_relative_value, {"lookback": lb, "asset_a": "QQQ", "asset_b": "IWM"}, f"Relative momentum: QQQ vs IWM {lb}M"))
    if has("SPY", "GLD"):
        for lb in [6, 12]:
            S.append(_cfg(f"RV_SPY_GLD_{lb}m", f"Equity vs Gold {lb}M", "Relative Value", wf_relative_value, {"lookback": lb, "asset_a": "SPY", "asset_b": "GLD"}, f"Relative momentum: SPY vs GLD {lb}M"))
    if has("SPY", "TLT"):
        S.append(_cfg("RV_SPY_TLT_12m", "Equity vs Long Bonds 12M", "Relative Value", wf_relative_value, {"lookback": 12, "asset_a": "SPY", "asset_b": "TLT"}, "Relative momentum: SPY vs TLT 12M"))

    # ── MULTI-TIMEFRAME ──────────────────────────────────────────
    if has("SPY", "IEF"):
        for slb, llb, sw in [(1, 12, 0.3), (3, 12, 0.4), (3, 9, 0.5), (1, 6, 0.3), (2, 10, 0.4), (6, 12, 0.5)]:
            S.append(_cfg(f"MTF_{slb}_{llb}_w{int(sw*10)}", f"Multi-TF {slb}M/{llb}M (w={sw})", "Multi-Timeframe", wf_multi_timeframe, {"short_lb": slb, "long_lb": llb, "short_weight": sw, "equity": "SPY", "bond": "IEF"}, f"Short {slb}M + Long {llb}M"))

    # ── COMPOSITE MACRO ──────────────────────────────────────────
    if ism is not None and cli is not None and has("SPY", "IEF"):
        S.append(_cfg("CMACRO_ISM_CLI", "Composite ISM+CLI", "Composite Macro", wf_composite_macro, {"indicators": [(ism, 50, 1, 1.0), (cli, 100, 2, 1.0)], "equity": "SPY", "bond": "IEF"}, "ISM>50 + CLI>100"))
    if ism is not None and vix is not None and has("SPY", "IEF"):
        S.append(_cfg("CMACRO_ISM_VIX", "Composite ISM+VIX", "Composite Macro", wf_composite_macro, {"indicators": [(ism, 50, 1, 1.0), (vix, 20, 0, 1.0)], "equity": "SPY", "bond": "IEF"}, "ISM>50 + VIX>20 (contrarian)"))
    if ism is not None and cli is not None and vix is not None and has("SPY", "IEF"):
        S.append(_cfg("CMACRO_TRIPLE", "Triple Macro (ISM+CLI+VIX)", "Composite Macro", wf_composite_macro, {"indicators": [(ism, 50, 1, 1.0), (cli, 100, 2, 1.0), (vix, 20, 0, 0.5)], "equity": "SPY", "bond": "IEF"}, "ISM + CLI + VIX contrarian"))
        S.append(_cfg("CMACRO_TRIPLE_HEAVY_ISM", "Triple Macro (ISM-heavy)", "Composite Macro", wf_composite_macro, {"indicators": [(ism, 50, 1, 2.0), (cli, 100, 2, 1.0), (vix, 20, 0, 0.5)], "equity": "SPY", "bond": "IEF"}, "ISM 2x weight + CLI + VIX"))
        S.append(_cfg("CMACRO_TRIPLE_STRICT", "Triple Macro (strict thresh)", "Composite Macro", wf_composite_macro, {"indicators": [(ism, 52, 1, 1.0), (cli, 100.5, 2, 1.0), (vix, 22, 0, 1.0)], "equity": "SPY", "bond": "IEF"}, "Higher thresholds"))

    # ── VOL-SCALED ───────────────────────────────────────────────
    if all(a in avail for a in MULTI5 + ["BIL"]):
        for lb, vw in [(6, 6), (12, 6), (6, 12), (12, 12)]:
            S.append(_cfg(f"VSMOM_{lb}m_v{vw}_5A", f"Vol-Scaled Mom {lb}M (v={vw}M, 5A)", "Vol-Scaled", wf_vol_scaled_momentum, {"lookback": lb, "vol_window": vw, "assets": MULTI5, "top_n": 2, "cash": "BIL"}, f"{lb}M momentum / {vw}M vol"))
    if all(a in avail for a in MULTI8 + ["BIL"]):
        for lb in [6, 12]:
            S.append(_cfg(f"VSMOM_{lb}m_v6_8A", f"Vol-Scaled Mom {lb}M (8-Asset)", "Vol-Scaled", wf_vol_scaled_momentum, {"lookback": lb, "vol_window": 6, "assets": MULTI8, "top_n": 3, "cash": "BIL"}, f"{lb}M momentum / 6M vol"))

    # ── ADAPTIVE ─────────────────────────────────────────────────
    if has("SPY", "IEF"):
        for slb, llb, vt in [(3, 12, 0.18), (3, 12, 0.22), (1, 12, 0.20), (3, 9, 0.18), (6, 12, 0.20), (3, 12, 0.15)]:
            S.append(_cfg(f"ADAPT_{slb}_{llb}_v{int(vt*100)}", f"Adaptive Mom {slb}M/{llb}M (vol>{int(vt*100)}%)", "Adaptive", wf_adaptive_momentum, {"short_lb": slb, "long_lb": llb, "vol_threshold": vt, "vol_window": 6, "equity": "SPY", "bond": "IEF"}, f"Use {slb}M when vol>{int(vt*100)}%"))

    # ── CORE-SATELLITE ───────────────────────────────────────────
    if has("SPY", "EFA", "EEM", "GLD", "TLT"):
        for cw, lb in [(0.6, 6), (0.6, 12), (0.5, 6), (0.7, 6)]:
            S.append(_cfg(f"CS_{int(cw*100)}core_{lb}m", f"Core-Satellite {int(cw*100)}/{int((1-cw)*100)} ({lb}M)", "Core-Satellite", wf_core_satellite, {"core_weight": cw, "core": {"SPY": 1.0}, "satellite": ["EFA", "EEM", "GLD", "TLT"], "lookback": lb, "top_n": 2}, f"{int(cw*100)}% SPY core"))
    if has("SPY", "AGG") and sum(1 for s in SECTORS if s in avail) >= 5:
        active_sectors = [s for s in SECTORS if s in avail]
        for lb in [3, 6]:
            S.append(_cfg(f"CS_6040_SEC_{lb}m", f"60/40 Core + Sector Satellite ({lb}M)", "Core-Satellite", wf_core_satellite, {"core_weight": 0.7, "core": {"SPY": 0.6, "AGG": 0.4}, "satellite": active_sectors, "lookback": lb, "top_n": 3}, f"70% 60/40 core, 30% top 3 sectors"))
    if all(a in avail for a in ["SPY", "AGG", "QQQ", "IWM", "EFA", "GLD", "DBC", "TLT"]):
        for cw in [0.5, 0.6]:
            S.append(_cfg(f"CS_BAL_{int(cw*100)}_BROAD", f"Balanced Core {int(cw*100)}% + Broad Sat", "Core-Satellite", wf_core_satellite, {"core_weight": cw, "core": {"SPY": 0.6, "AGG": 0.4}, "satellite": ["QQQ", "IWM", "EFA", "GLD", "DBC", "TLT"], "lookback": 6, "top_n": 2}, f"{int(cw*100)}% balanced core"))

    # ── RISK-ON/OFF ──────────────────────────────────────────────
    if has("SPY", "IEF"):
        S.append(_cfg("RORO_2SIG_TM", "RORO 2-Signal (Trend+Mom)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "2 signals: 10M SMA + 12M momentum"))
        S.append(_cfg("RORO_3SIG_TMD", "RORO 3-Signal (T+M+DD)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("drawdown", {"lb": 12, "thresh": -0.10})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "3 signals: trend + momentum + drawdown"))
        S.append(_cfg("RORO_3SIG_TMD_STRICT", "RORO 3-Signal Strict", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 8}), ("momentum", {"lb": 6}), ("drawdown", {"lb": 12, "thresh": -0.05})], "equity": "SPY", "bond": "IEF", "threshold": 0.67}, "3 signals strict: 2/3 needed"))
        S.append(_cfg("RORO_2SIG_FAST", "RORO 2-Signal Fast", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 5}), ("momentum", {"lb": 6})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "Fast: 5M SMA + 6M momentum"))
    if ism is not None and has("SPY", "IEF"):
        S.append(_cfg("RORO_4SIG_TMDM", "RORO 4-Signal (T+M+DD+ISM)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("drawdown", {"lb": 12, "thresh": -0.10}), ("macro", {"data": ism, "thresh": 50, "lag": 1})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "4 signals: trend+momentum+drawdown+ISM"))
        S.append(_cfg("RORO_4SIG_STRICT", "RORO 4-Signal Strict (3/4)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 8}), ("momentum", {"lb": 9}), ("drawdown", {"lb": 12, "thresh": -0.08}), ("macro", {"data": ism, "thresh": 50, "lag": 1})], "equity": "SPY", "bond": "IEF", "threshold": 0.75}, "4 signals: need 3/4"))
    if cli is not None and has("SPY", "IEF"):
        S.append(_cfg("RORO_3SIG_TMC", "RORO 3-Signal (T+M+CLI)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 10}), ("momentum", {"lb": 12}), ("macro", {"data": cli, "thresh": 100, "lag": 2})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "3 signals: trend+momentum+CLI"))
        S.append(_cfg("RORO_3SIG_TMC_FAST", "RORO 3-Signal Fast (T+M+CLI)", "Risk-On/Off", wf_roro, {"signals": [("trend", {"sma": 6}), ("momentum", {"lb": 6}), ("macro", {"data": cli, "thresh": 100, "lag": 2})], "equity": "SPY", "bond": "IEF", "threshold": 0.5}, "Fast: 6M SMA + 6M momentum + CLI"))

    # ── CROSS-ASSET ROTATION ─────────────────────────────────────
    all_rotate = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC"]
    if sum(1 for a in all_rotate if a in avail) >= 5 and has("BIL"):
        active_rotate = [a for a in all_rotate if a in avail]
        for lb, tn in [(6, 2), (6, 3), (12, 2), (12, 3)]:
            S.append(_cfg(f"XROT_{lb}m_T{tn}", f"Cross-Asset Rotation {lb}M Top {tn}", "Cross-Asset", wf_cross_asset_rotation, {"lookback": lb, "assets": active_rotate, "top_n": tn, "cash": "BIL"}, f"Top {tn} of 7 by {lb}M return"))
        for tn in [2, 3]:
            S.append(_cfg(f"XROT_13612W_T{tn}", f"Cross-Asset 13612W Top {tn}", "Cross-Asset", wf_cross_asset_rotation, {"lookback": 12, "assets": active_rotate, "top_n": tn, "cash": "BIL", "use_13612w": True}, f"Top {tn} of 7 by 13612W score"))
    if has("SPY", "TLT", "GLD", "BIL"):
        for lb in [6, 12]:
            S.append(_cfg(f"XROT_{lb}m_3A", f"3-Asset Rotation {lb}M", "Cross-Asset", wf_cross_asset_rotation, {"lookback": lb, "assets": ["SPY", "TLT", "GLD"], "top_n": 1, "cash": "BIL"}, f"Best of SPY/TLT/GLD by {lb}M"))

    # ── TREND + VOL ──────────────────────────────────────────────
    if has("SPY", "IEF"):
        for sma, vc in [(8, 0.18), (8, 0.22), (10, 0.18), (10, 0.22), (10, 0.25), (12, 0.20)]:
            S.append(_cfg(f"TVF_{sma}m_v{int(vc*100)}", f"Trend({sma}M)+VolFilter({int(vc*100)}%)", "Trend+Vol", wf_trend_vol_filter, {"sma_months": sma, "vol_window": 6, "vol_cap": vc, "equity": "SPY", "bond": "IEF"}, f"{sma}M SMA trend, reduce when vol>{int(vc*100)}%"))

    # ── EQUITY ROTATION ──────────────────────────────────────────
    eq_universe = ["SPY", "QQQ", "IWM"]
    if all(a in avail for a in eq_universe) and has("IEF"):
        for lb in [3, 6, 12]:
            S.append(_cfg(f"EQROT_{lb}m_3E", f"Equity Rotation {lb}M (SPY/QQQ/IWM)", "Equity Rotation", wf_equity_rotation, {"lookback": lb, "equities": eq_universe, "bond": "IEF", "top_n": 1}, f"Best of SPY/QQQ/IWM by {lb}M"))
        for lb in [6, 12]:
            S.append(_cfg(f"EQROT_{lb}m_SMA10", f"Equity Rotation {lb}M + 10M SMA Filter", "Equity Rotation", wf_equity_rotation, {"lookback": lb, "equities": eq_universe, "bond": "IEF", "top_n": 1, "sma_filter": 10}, f"Best equity by {lb}M, must be above 10M SMA"))
    eq5 = ["SPY", "QQQ", "IWM", "EFA", "EEM"]
    if all(a in avail for a in eq5) and has("IEF"):
        for lb in [6, 12]:
            S.append(_cfg(f"EQROT_{lb}m_5E", f"Equity Rotation {lb}M (5 ETFs)", "Equity Rotation", wf_equity_rotation, {"lookback": lb, "equities": eq5, "bond": "IEF", "top_n": 2}, f"Top 2 of 5 equity ETFs by {lb}M"))
        S.append(_cfg("EQROT_13612W_5E", "Equity Rotation 13612W (5 ETFs)", "Equity Rotation", wf_equity_rotation, {"lookback": 12, "equities": eq5, "bond": "IEF", "top_n": 2, "sma_filter": 10}, "Top 2 of 5, 12M mom + 10M SMA filter"))

    # ── CANARY ───────────────────────────────────────────────────
    if has("SPY", "EFA", "EEM", "QQQ", "IWM", "TLT", "IEF", "GLD", "BIL"):
        S.append(_cfg("CANARY_BAA_BROAD", "Canary BAA (Broad)", "Canary", wf_canary, {"canary": ["SPY", "EFA"], "offensive": ["SPY", "QQQ", "IWM", "EFA", "EEM"], "defensive": ["TLT", "IEF", "GLD", "BIL"], "off_top_n": 3, "def_top_n": 2}, "SPY/EFA canary, 5 offensive, 4 defensive"))
        S.append(_cfg("CANARY_BAA_AGG", "Canary BAA (Aggressive)", "Canary", wf_canary, {"canary": ["SPY", "EFA"], "offensive": ["SPY", "QQQ", "IWM", "EFA", "EEM"], "defensive": ["TLT", "IEF", "GLD", "BIL"], "off_top_n": 1, "def_top_n": 1}, "BAA aggressive: concentrate in top 1"))
        S.append(_cfg("CANARY_EEM", "Canary (EEM Detector)", "Canary", wf_canary, {"canary": ["EEM"], "offensive": ["SPY", "QQQ", "EFA"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}, "EEM as single canary"))
    if has("SPY", "EFA", "AGG", "TLT", "GLD", "BIL"):
        S.append(_cfg("CANARY_AGG", "Canary (AGG+EFA Detector)", "Canary", wf_canary, {"canary": ["AGG", "EFA"], "offensive": ["SPY", "QQQ", "EFA", "EEM"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}, "AGG+EFA as canary pair"))
        S.append(_cfg("CANARY_4C", "Canary (4 Canaries)", "Canary", wf_canary, {"canary": ["SPY", "EFA", "EEM", "AGG"], "offensive": ["SPY", "QQQ", "IWM"], "defensive": ["TLT", "GLD", "BIL"], "off_top_n": 2, "def_top_n": 2}, "4-canary universe"))

    return S


# ════════════════════════════════════════════════════════════════════
# BATCH STRATEGY ADAPTER
# ════════════════════════════════════════════════════════════════════



def build_batch_registry(
    available_assets: set[str] | None = None,
    use_macro_placeholders: bool = True,
) -> list[BatchStrategy]:
    """Build all batch strategies as production Strategy objects.

    Parameters
    ----------
    available_assets
        Set of ticker names to include.  ``None`` = all known assets.
    use_macro_placeholders
        If True (default), macro params are string placeholders resolved
        at backtest time inside ``BatchStrategy.initialize()``.
        If False, load live Series now (for Streamlit compatibility).
    """
    if use_macro_placeholders:
        macro: dict[str, Any] = {
            "ISM_PMI": "ISM_PMI",
            "OECD_CLI": "OECD_CLI",
            "VIX": "VIX",
        }
    else:
        macro = {}
        for name, code in MACRO_CODES.items():
            try:
                s = DbSeries(code)
                if s is not None and not s.empty:
                    macro[name] = s.sort_index()
            except Exception:
                pass

    configs = _build_configs(available_assets=available_assets, macro_data=macro)
    return [BatchStrategy(cfg) for cfg in configs]
