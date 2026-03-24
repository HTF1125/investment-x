"""Macro outlook API -- serves precomputed regime/allocation data.

Endpoints read from the macro_outlook DB table (populated by the scheduler).
The POST /macro/refresh endpoint triggers a background recompute for admins.
"""  # noqa: E501

from __future__ import annotations

import threading

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request

from ix.api.dependencies import get_current_admin_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter

from ix.db.models.api_cache import ApiCache
from ix.db.conn import Session as SessionCtx
from ix.db.models.macro_outlook import MacroOutlook
from ix.db.models.macro_regime_strategy import MacroRegimeStrategy
from ix.core.macro.config import TARGET_INDICES
from ix.misc import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/macro/targets")
@_limiter.limit("60/minute")
def list_targets(request: Request, _user=Depends(get_optional_user)):
    """List all available target indices for macro outlook."""
    targets = []
    for name, idx in TARGET_INDICES.items():
        targets.append(
            {
                "name": name,
                "ticker": idx.ticker,
                "region": idx.region,
                "currency": idx.currency,
                "has_sectors": idx.has_sectors,
            }
        )
    return {"targets": targets}


@router.get("/macro/outlook")
def get_outlook(target: str = "S&P 500", _user=Depends(get_optional_user)):
    """Return the snapshot JSON for a target index.

    The snapshot contains current regime, probabilities, indicator readings,
    forward projections, transition matrix, and regime statistics.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
            .filter_by(target_name=target)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Macro outlook not computed yet. Admin must trigger computation.",
            )
        return {
            "target_name": row.target_name,
            "computed_at": row.computed_at.isoformat(),
            "snapshot": row.snapshot,
        }


@router.get("/macro/timeseries")
def get_timeseries(target: str = "S&P 500", _user=Depends(get_optional_user)):
    """Return the time series JSON for a target index.

    Contains historical composites (growth, inflation, liquidity, tactical),
    allocation weights, regime probabilities, and target prices.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
            .filter_by(target_name=target)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Macro outlook not computed yet. Admin must trigger computation.",
            )
        return {
            "target_name": row.target_name,
            "computed_at": row.computed_at.isoformat(),
            "timeseries": row.timeseries,
        }


@router.get("/macro/backtest")
def get_backtest(target: str = "S&P 500", _user=Depends(get_optional_user)):
    """Return the backtest JSON for a target index.

    Contains equity curves (strategy, benchmark, 100% index), allocation
    weight history, and performance statistics.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
            .filter_by(target_name=target)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Macro outlook not computed yet. Admin must trigger computation.",
            )
        return {
            "target_name": row.target_name,
            "computed_at": row.computed_at.isoformat(),
            "backtest": row.backtest,
        }


@router.get("/macro/stress-test")
@_limiter.limit("10/minute")
def get_stress_test(request: Request, target: str = "KOSPI", _user=Depends(get_optional_user)):
    """Compute stress test analysis for a target index.

    Auto-detects historical crash events, computes forward returns at
    standard horizons, and builds recovery curves.
    """
    if target not in TARGET_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{target}'. Available: {list(TARGET_INDICES.keys())}",
        )
    try:
        from ix.core.stress_test import compute_stress_test

        result = compute_stress_test(target)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception(f"Stress test failed for {target}")
        raise HTTPException(status_code=500, detail="Stress test computation failed")


def _refresh_target(target_name: str) -> None:
    """Background worker to recompute macro outlook for a single target."""
    try:
        from ix.core.macro.pipeline import compute_and_save

        logger.info(f"Background refresh started for {target_name}")
        compute_and_save(target_name)
        logger.info(f"Background refresh completed for {target_name}")
    except Exception as e:
        logger.warning(f"Background refresh failed for {target_name}: {e}")


@router.post("/macro/refresh")
def refresh_outlook(
    target: str = "S&P 500", _user=Depends(get_current_admin_user)
):
    """Trigger a background recompute of macro outlook for a target index.

    Admin-only. Returns immediately; computation runs in a background thread.
    """
    if target not in TARGET_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{target}'. Available: {list(TARGET_INDICES.keys())}",
        )

    thread = threading.Thread(
        target=_refresh_target,
        args=(target,),
        daemon=True,
        name=f"macro-refresh-{target}",
    )
    thread.start()

    return {
        "status": "Computing in background",
        "target": target,
        "message": f"Refresh triggered for {target}. Check /api/macro/outlook?target={target} in a few minutes.",
    }


# ===========================================================================
# REGIME STRATEGY ENDPOINTS
# ===========================================================================


@router.get("/macro/regime-strategy/indices")
@_limiter.limit("30/minute")
def list_regime_strategy_indices(request: Request, _user=Depends(get_optional_user)):
    """List indices with precomputed regime strategy data."""
    with SessionCtx() as session:
        rows = session.query(MacroRegimeStrategy.index_name).all()
        return {"indices": [r[0] for r in rows]}


@router.get("/macro/regime-strategy/backtest")
@_limiter.limit("30/minute")
def get_regime_strategy_backtest(request: Request, index: str = "ACWI", _user=Depends(get_optional_user)):
    """Return precomputed walk-forward backtest results for a single index."""
    with SessionCtx() as session:
        row = (
            session.query(MacroRegimeStrategy)
            .filter_by(index_name=index)
            .first()
        )
        if not row:
            raise HTTPException(404, f"No regime strategy data for '{index}'.")
        return {
            "index_name": row.index_name,
            "computed_at": row.computed_at.isoformat(),
            "backtest": row.backtest,
        }


@router.get("/macro/regime-strategy/factors")
@_limiter.limit("30/minute")
def get_regime_strategy_factors(request: Request, index: str = "ACWI", _user=Depends(get_optional_user)):
    """Return factor selection history for a single index."""
    with SessionCtx() as session:
        row = (
            session.query(MacroRegimeStrategy)
            .filter_by(index_name=index)
            .first()
        )
        if not row:
            raise HTTPException(404, f"No regime strategy data for '{index}'.")
        return {
            "index_name": row.index_name,
            "computed_at": row.computed_at.isoformat(),
            "factors": row.factors,
        }


@router.get("/macro/regime-strategy/signal")
@_limiter.limit("30/minute")
def get_regime_strategy_signal(request: Request, index: str = "ACWI", _user=Depends(get_optional_user)):
    """Return current signal readings for a single index."""
    with SessionCtx() as session:
        row = (
            session.query(MacroRegimeStrategy)
            .filter_by(index_name=index)
            .first()
        )
        if not row:
            raise HTTPException(404, f"No regime strategy data for '{index}'.")
        return {
            "index_name": row.index_name,
            "computed_at": row.computed_at.isoformat(),
            "current_signal": row.current_signal,
        }


@router.get("/macro/regime-strategy/summary")
@_limiter.limit("30/minute")
def get_regime_strategy_summary(request: Request, _user=Depends(get_optional_user)):
    """Compact summary of all indices -- for dashboard widget."""
    with SessionCtx() as session:
        rows = session.query(MacroRegimeStrategy).all()
        if not rows:
            raise HTTPException(404, "No regime strategy data computed yet.")
        indices = []
        for row in rows:
            sig = row.current_signal or {}
            cat_sigs = sig.get("category_signals", {})
            # Pick the Blended or first available signal for headline
            headline = cat_sigs.get("Blended") or cat_sigs.get("Growth") or {}
            regime_sig = cat_sigs.get("Regime", {})
            # Extract backtest performance from Blended strategy
            bt = row.backtest or {}
            strats = bt.get("strategies", {})
            blended = strats.get("Blended") or next(iter(strats.values()), {})

            indices.append({
                "index_name": row.index_name,
                "computed_at": row.computed_at.isoformat(),
                "eq_weight": headline.get("eq_weight"),
                "label": headline.get("label", ""),
                "regime": regime_sig.get("regime", ""),
                "growth_pctile": regime_sig.get("growth_pctile"),
                "inflation_pctile": regime_sig.get("inflation_pctile"),
                "category_signals": cat_sigs,
                "sharpe": blended.get("sharpe"),
                "alpha": blended.get("alpha"),
                "max_dd": blended.get("max_dd"),
                "ann_return": blended.get("ann_return"),
            })
        return {"indices": indices}


@router.post("/macro/regime-strategy/refresh")
def refresh_regime_strategy(
    index: str = "ACWI", _user=Depends(get_current_admin_user)
):
    """Admin-only: trigger background recompute for a single index."""
    from ix.core.macro.wf_backtest import INDEX_MAP

    if index not in INDEX_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown index '{index}'. Available: {list(INDEX_MAP.keys())}",
        )

    def _worker(idx: str):
        try:
            from ix.core.macro.wf_compute import compute_and_save
            compute_and_save(idx)
        except Exception as e:
            logger.warning(f"Regime strategy refresh failed for {idx}: {e}")

    thread = threading.Thread(
        target=_worker, args=(index,), daemon=True,
        name=f"regime-strategy-{index}",
    )
    thread.start()
    return {"status": "Computing in background", "index": index}


# ===========================================================================
# VAMS REGIME ENDPOINTS
# ===========================================================================

from ix.core.macro.vams import (
    compute_vams_series as _vectorized_vams,
    score_to_regime as _score_to_regime,
    weeks_in_regime as _weeks_in_regime,
    period_return as _period_return,
    compute_cacri as _compute_cacri,
)


@router.get("/macro/technicals")
@_limiter.limit("30/minute")
def get_vams_regimes(request: Request, index: str | None = None, _user=Depends(get_optional_user)):
    """VAMS momentum regime data for all global indices.

    Returns current regime, VAMS scores, daily prices (5yr), weekly VAMS
    series, performance returns, and cross-asset CACRI.
    Serves from DB cache; falls back to live compute on cache miss.

    When `index` is provided, only that index includes heavy data
    (daily_prices, weekly_vams, vomo.history). All other indices return
    lightweight summaries only (~92% bandwidth reduction).
    """
    with SessionCtx() as session:
        entry = session.query(ApiCache).get("technicals")
        if entry and entry.value:
            return _strip_heavy_fields(entry.value, index)

    return _strip_heavy_fields(_compute_vams_response(), index)


def _strip_heavy_fields(response: dict, selected_index: str | None) -> dict:
    """Strip heavy OHLCV/VAMS data from non-selected indices.

    If selected_index is None, returns the full response unchanged (backwards compatible).
    Otherwise, only the matching index keeps daily_prices, weekly_vams, and vomo.history.
    """
    if selected_index is None:
        return response

    stripped_indices = []
    for idx in response.get("indices", []):
        if idx["name"] == selected_index:
            stripped_indices.append(idx)
        else:
            light = {k: v for k, v in idx.items() if k not in ("daily_prices", "weekly_vams")}
            # Keep VOMO scores but strip the heavy history array
            if "vomo" in idx:
                light["vomo"] = {k: v for k, v in idx["vomo"].items() if k != "history"}
            stripped_indices.append(light)

    return {**response, "indices": stripped_indices}
INDEX_YF: dict[str, str] = {
    "S&P 500":      "ES=F",
    "Nasdaq 100":   "NQ=F",
    "Russell2K" : "RTY=F",
    "DAX":          "^GDAXI",
    "Nikkei 225":   "^N225",
    "KOSPI":        "^KS11",
    "Dollar":       "^NYICDX",
    "USDKRW":       "USDKRW=X",
    "Gold":         "GC=F",
    "Silver":       "SI=F",
    "Treasury 2Y": "ZT=F",
    "Treasury 10Y": "ZN=F",
    "Bitcoin" : "BTC-USD",
}

CROSS_ASSET_YF: dict[str, str] = {
    "SPY": "SPY", "TLT": "TLT", "HYG": "HYG", "LQD": "LQD",
    "DBC": "DBC", "GLD": "GLD", "EEM": "EEM", "UUP": "UUP",
}


def _resample_weekly(s: pd.Series) -> pd.Series:
    """Resample daily close to weekly (Wednesday)."""
    if s.empty:
        return s
    return s.resample("W-WED").last().ffill().dropna()


def _compute_vams_response() -> dict:
    """Compute full VAMS response via crawler (yfinance), persist to DB cache."""
    from ix.misc.crawler import get_yahoo_data

    SHORT_W, MEDIUM_W = 4, 13
    FIVE_YEARS_AGO = pd.Timestamp.now() - pd.DateOffset(years=5)

    def _compute_vomo(df: pd.DataFrame, days: int) -> float | None:
        """VOMO = Return% / Average ATR% over the period."""
        if len(df) < days + 1:
            return None
        recent = df.tail(days + 1)
        close = recent["Close"].squeeze()
        high = recent["High"].squeeze()
        low = recent["Low"].squeeze()
        prev_close = close.shift(1)

        ret_pct = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        # True Range = max(H-L, |H-prevC|, |L-prevC|)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        avg_atr_pct = (tr / close).mean() * 100

        if avg_atr_pct == 0 or pd.isna(avg_atr_pct):
            return None
        return round(ret_pct / avg_atr_pct, 2)

    def _compute_vomo_history(df: pd.DataFrame) -> dict:
        """Compute weekly rolling VOMO composite series for chart shading."""
        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        prev_close = close.shift(1)

        # True Range series
        tr = pd.concat([
            high - low, (high - prev_close).abs(), (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr_pct = tr / close  # as fraction of price

        results_dates = []
        results_values = []

        # Compute weekly (every 5 trading days) for efficiency
        indices = list(range(252, len(df), 5))  # start after 1Y warmup
        if indices and indices[-1] != len(df) - 1:
            indices.append(len(df) - 1)  # always include latest

        for i in indices:
            composites = []
            for days, weight in [(21, 0.2), (126, 0.4), (252, 0.4)]:
                if i < days:
                    continue
                ret_pct = (float(close.iloc[i]) / float(close.iloc[i - days]) - 1) * 100
                avg_atr = float(atr_pct.iloc[i - days:i].mean()) * 100
                if avg_atr > 0:
                    composites.append((weight, ret_pct / avg_atr))
            if composites:
                total_w = sum(w for w, _ in composites)
                comp = sum(w * v for w, v in composites) / total_w if total_w > 0 else 0
                results_dates.append(df.index[i].strftime("%Y-%m-%d"))
                results_values.append(round(comp, 2))

        return {"dates": results_dates, "values": results_values}

    def _compute_index(name: str, yf_ticker: str) -> dict | None:
        try:
            df = get_yahoo_data(yf_ticker)
            if df.empty or len(df) < 100:
                return None

            close = df["Close"].squeeze().dropna()
            weekly = _resample_weekly(close)
            if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
                return None

            vams_scores = _vectorized_vams(weekly, SHORT_W, MEDIUM_W)
            valid_scores = vams_scores.dropna()
            if valid_scores.empty:
                return None

            current_score = int(valid_scores.iloc[-1])
            regime = _score_to_regime(current_score)
            weeks_in = _weeks_in_regime(valid_scores)

            # VOMO: Volatility-adjusted Momentum (Scott Bennett / InvestWithRules)
            vomo_1m = _compute_vomo(df, 21)
            vomo_6m = _compute_vomo(df, 126)
            vomo_1y = _compute_vomo(df, 252)

            vomo_composite = None
            if vomo_1m is not None and vomo_6m is not None and vomo_1y is not None:
                vomo_composite = round(0.2 * vomo_1m + 0.4 * vomo_6m + 0.4 * vomo_1y, 2)

            # Rolling VOMO history for chart background shading
            vomo_history = _compute_vomo_history(df)

            # 5-year OHLCV for charts
            df_5y = df[df.index >= FIVE_YEARS_AGO].dropna(subset=["Close"])

            return {
                "name": name,
                "regime": regime,
                "score": current_score,
                "price": round(float(close.iloc[-1]), 2),
                "ret_1m": _period_return(close, 4),
                "ret_3m": _period_return(close, 13),
                "ret_6m": _period_return(close, 26),
                "ret_1y": _period_return(close, 52),
                "weeks_in_regime": weeks_in,
                "vomo": {
                    "1m": vomo_1m,
                    "6m": vomo_6m,
                    "1y": vomo_1y,
                    "composite": vomo_composite,
                    "history": vomo_history,
                },
                "daily_prices": {
                    "dates":  [d.strftime("%Y-%m-%d") for d in df_5y.index],
                    "open":   [round(float(v), 2) for v in df_5y["Open"].values],
                    "high":   [round(float(v), 2) for v in df_5y["High"].values],
                    "low":    [round(float(v), 2) for v in df_5y["Low"].values],
                    "close":  [round(float(v), 2) for v in df_5y["Close"].values],
                    "volume": [int(v) if not pd.isna(v) else 0 for v in df_5y["Volume"].values],
                },
                "weekly_vams": {
                    "dates": [d.strftime("%Y-%m-%d") for d in valid_scores.index],
                    "scores": [int(v) for v in valid_scores.values],
                },
            }
        except Exception:
            logger.exception(f"Failed to compute VAMS regime for {name}")
            return None

    def _compute_cross_asset(ca_name: str, yf_ticker: str) -> tuple[str, int] | None:
        try:
            df = get_yahoo_data(yf_ticker)
            if df.empty:
                return None
            close = df["Close"].squeeze().dropna()
            weekly = _resample_weekly(close)
            if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
                return None
            ca_scores = _vectorized_vams(weekly, SHORT_W, MEDIUM_W).dropna()
            if ca_scores.empty:
                return None
            return (ca_name, int(ca_scores.iloc[-1]))
        except Exception:
            logger.warning(f"Failed to compute cross-asset VAMS for {ca_name}")
            return None

    from concurrent.futures import ThreadPoolExecutor, as_completed

    indices = []
    cross_asset_vams: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        idx_futures = {
            pool.submit(_compute_index, name, yf_ticker): name
            for name, yf_ticker in INDEX_YF.items()
        }
        ca_futures = {
            pool.submit(_compute_cross_asset, ca_name, yf_ticker): ca_name
            for ca_name, yf_ticker in CROSS_ASSET_YF.items()
        }

        for future in as_completed(idx_futures):
            result = future.result()
            if result is not None:
                indices.append(result)

        for future in as_completed(ca_futures):
            result = future.result()
            if result is not None:
                cross_asset_vams[result[0]] = result[1]

    name_order = {name: i for i, name in enumerate(INDEX_YF)}
    indices.sort(key=lambda d: name_order.get(d["name"], 999))

    cacri = _compute_cacri(cross_asset_vams)

    response = {
        "indices": indices,
        "cacri": cacri,
        "cross_asset_vams": cross_asset_vams,
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }

    # Persist to DB cache
    with SessionCtx() as session:
        entry = session.query(ApiCache).get("technicals")
        if entry:
            entry.value = response
        else:
            session.add(ApiCache(key="technicals", value=response))

    return response


@router.get("/macro/cacri-history")
@_limiter.limit("30/minute")
def get_cacri_history(request: Request, _user=Depends(get_optional_user)):
    """Historical CACRI timeseries: weekly fraction of cross-asset proxies with bearish VAMS.

    Returns weekly CACRI values plus per-asset VAMS score timeseries.
    Serves from DB cache; falls back to live compute on cache miss.
    """
    with SessionCtx() as session:
        entry = session.query(ApiCache).get("cacri-history")
        if entry and entry.value:
            return entry.value

    return _compute_cacri_history()


def _compute_cacri_history() -> dict:
    """Compute full CACRI history response via crawler, persist to DB cache."""
    from ix.misc.crawler import get_yahoo_data

    SHORT_W, MEDIUM_W = 4, 13

    # Compute weekly VAMS for each cross-asset proxy
    all_scores: dict[str, pd.Series] = {}
    for ca_name, yf_ticker in CROSS_ASSET_YF.items():
        try:
            df = get_yahoo_data(yf_ticker)
            if df.empty:
                continue
            close = df["Close"].squeeze().dropna()
            weekly = _resample_weekly(close)
            if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
                continue
            scores = _vectorized_vams(weekly, SHORT_W, MEDIUM_W).dropna()
            if not scores.empty:
                all_scores[ca_name] = scores
        except Exception:
            logger.warning(f"CACRI history: failed for {ca_name}")

    if not all_scores:
        return {"dates": [], "cacri": [], "assets": {}}

    # Align all score series on a common weekly index
    df = pd.DataFrame(all_scores)
    df = df.dropna(how="all")

    # CACRI at each point = fraction of non-null assets with score <= -1
    def _row_cacri(row: pd.Series) -> float | None:
        valid = row.dropna()
        if valid.empty:
            return None
        return round(float((valid <= -1).sum() / len(valid)), 4)

    cacri_series = df.apply(_row_cacri, axis=1).dropna()

    # Build per-asset score timeseries for the chart
    assets: dict[str, dict] = {}
    for col in df.columns:
        s = df[col].dropna()
        assets[col] = {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "scores": [int(v) for v in s.values],
        }

    response = {
        "dates": [d.strftime("%Y-%m-%d") for d in cacri_series.index],
        "cacri": [round(float(v) * 100, 1) for v in cacri_series.values],
        "assets": assets,
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }

    # Persist to DB cache
    with SessionCtx() as session:
        entry = session.query(ApiCache).get("cacri-history")
        if entry:
            entry.value = response
        else:
            session.add(ApiCache(key="cacri-history", value=response))

    return response


@router.post("/macro/technicals/refresh")
@_limiter.limit("5/minute")
def refresh_vams_regimes(request: Request, _user=Depends(get_optional_user)):
    """Force refresh: clear DB cache and recompute VAMS regimes + CACRI history."""
    from ix.db.query import clear_series_cache
    clear_series_cache()

    # Clear both cache entries
    with SessionCtx() as session:
        for key in ("technicals", "cacri-history"):
            entry = session.query(ApiCache).get(key)
            if entry:
                session.delete(entry)

    # Recompute both
    response = _compute_vams_response()
    _compute_cacri_history()
    return response
