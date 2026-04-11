"""Regimes API — generic endpoints for any registered regime model.

Reads precomputed snapshots from the ``regime_snapshot`` DB table.
The POST /regimes/{key}/refresh endpoint triggers a background recompute
for admins.

Models are discovered from ``ix.core.regimes.registry`` at import time —
new regime models auto-appear here without code changes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger
from ix.core.regimes import (
    compute_regime,
    get_regime,
    list_regimes,
)
from ix.core.regimes.compose import compose_regimes
from ix.db.models import RegimeSnapshot, regime_fingerprint

router = APIRouter()
logger = get_logger(__name__)

# Bounded executor for background refresh tasks
_refresh_executor = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="regime-refresh"
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _lookup_snapshot(db: SessionType, key: str) -> RegimeSnapshot:
    """Load the snapshot row for a regime key using its default params."""
    try:
        reg = get_regime(key)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Regime '{key}' is not registered.",
        )

    fp = regime_fingerprint(key, reg.default_params)
    row = db.get(RegimeSnapshot, fp)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Regime '{key}' not computed yet. "
                f"Admin must trigger POST /api/regimes/{key}/refresh."
            ),
        )
    return row


# ─────────────────────────────────────────────────────────────────────
# List models
# ─────────────────────────────────────────────────────────────────────


@router.get("/regimes/models")
@_limiter.limit("60/minute")
def list_models(request: Request, _user=Depends(get_optional_user)):
    """List all registered regime models with embedded quality snapshot."""
    models = []
    for reg in list_regimes():
        models.append({
            "key": reg.key,
            "display_name": reg.display_name,
            "description": reg.description,
            "states": reg.states,
            "dimensions": reg.dimensions,
            "has_strategy": reg.has_strategy,
            "category": reg.category,
            "phase_pair": reg.phase_pair,
            "color_map": reg.color_map,
            "dimension_colors": reg.dimension_colors,
            "state_descriptions": reg.state_descriptions,
            "default_params": reg.default_params,
        })
    return {"models": models}


# ─────────────────────────────────────────────────────────────────────
# Universal quality snapshot
# ─────────────────────────────────────────────────────────────────────
# Dynamic regime composition (axis × axis)
# ─────────────────────────────────────────────────────────────────────


# In-process cache for compose results — same params + same key set
# always produces the same composite, so cache by canonical key.
_COMPOSE_CACHE: dict[str, dict] = {}


@router.get("/regimes/compose")
@_limiter.limit("30/minute")
def compose_regimes_endpoint(
    request: Request,
    keys: str,  # comma-separated regime keys
    _user=Depends(get_optional_user),
):
    """Compose 2+ axis regimes into a custom multi-axis composite.

    Query params:
        keys: comma-separated regime keys (e.g. "growth,inflation").
              All must be category="axis". Order doesn't matter — the
              composite is normalized to sorted order internally.

    Returns:
        Snapshot dict with the same shape as a regular regime endpoint plus
        a synthesized "model" block (display_name, color_map, states, etc.)
        for the frontend.
    """
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    if len(key_list) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 regime keys to compose (comma-separated).",
        )

    cache_key = "+".join(sorted(set(key_list)))
    if cache_key in _COMPOSE_CACHE:
        return _COMPOSE_CACHE[cache_key]

    try:
        result = compose_regimes(key_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Compose endpoint failed for keys=%s", key_list)
        raise HTTPException(
            status_code=500,
            detail=f"Compose computation failed: {type(e).__name__}: {e}",
        )

    _COMPOSE_CACHE[cache_key] = result
    return result


# ── Ensemble endpoint ──────────────────────────────────────────────
_ENSEMBLE_CACHE: dict[str, dict] = {}


@router.get("/regimes/ensemble")
@_limiter.limit("10/minute")
def ensemble_endpoint(
    request: Request,
    universe: str = "broad",
    _user=Depends(get_optional_user),
):
    """IC-weighted multi-regime ensemble backtest.

    Combines ALL registered regimes optimally per asset using walk-forward
    IC-weighted signal combination.  Expensive on first call (~15-45s);
    cached in-process after.

    Query params:
        universe: ``"broad"`` (11 ETFs, default) or ``"equity"``
                  (SPY/IWM/EFA/EEM + BIL).

    Returns a StrategyData-compatible dict plus ensemble-specific metadata
    (``current_weights``, ``regime_drivers``, ``ensemble_meta``).
    """
    from ix.core.regimes.compute import UNIVERSE_PRESETS

    if universe not in UNIVERSE_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown universe '{universe}'. Choose from: {list(UNIVERSE_PRESETS.keys())}",
        )

    if universe in _ENSEMBLE_CACHE:
        return _ENSEMBLE_CACHE[universe]

    try:
        from ix.core.regimes.ensemble import compute_ensemble_strategy
        result = compute_ensemble_strategy(tickers=UNIVERSE_PRESETS[universe])
    except Exception as e:
        logger.exception("Ensemble computation failed for universe=%s", universe)
        raise HTTPException(
            status_code=500,
            detail=f"Ensemble computation failed: {type(e).__name__}: {e}",
        )

    if result is None:
        raise HTTPException(status_code=500, detail="Ensemble returned no data")

    _ENSEMBLE_CACHE[universe] = result
    return result


# ─────────────────────────────────────────────────────────────────────
# Per-model data endpoints
# ─────────────────────────────────────────────────────────────────────


@router.get("/regimes/{key}/current")
@_limiter.limit("30/minute")
def get_current_state(
    request: Request,
    key: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Return the current state snapshot for a regime model.

    Injects per-dimension Z history (last 24 months) and 3M acceleration
    into ``current_state.dimensions[dim]`` so AxisDock tiles can render a
    sparkline + cycle direction without hitting the timeseries endpoint.
    Also mirrors those values onto a top-level ``input_states[key]`` block
    for tiles that operate in single-axis mode.
    """
    row = _lookup_snapshot(db, key)
    cs = dict(row.current_state or {})  # shallow copy — don't mutate JSONB
    ts = row.timeseries or {}
    composites = ts.get("composites") or {}
    dims_block = dict(cs.get("dimensions") or {})

    # For each dimension card, slice the trailing 24 z-score values from
    # the timeseries["composites"] block and compute a 3-month acceleration
    # (z[-1] - z[-3]). Skip cleanly if the column is missing.
    for dim_name in list(dims_block.keys()):
        z_col = f"{dim_name}_Z"
        z_series = composites.get(z_col) or []
        if not z_series:
            continue
        clean = [float(v) for v in z_series if v is not None]
        if not clean:
            continue
        history = clean[-24:]
        accel = None
        if len(clean) >= 3:
            accel = float(clean[-1] - clean[-3])
        dim_card = dict(dims_block[dim_name])
        dim_card.setdefault("history", history)
        dim_card.setdefault("acceleration", accel)
        dims_block[dim_name] = dim_card

    cs["dimensions"] = dims_block
    return {
        "regime_type": row.regime_type,
        "computed_at": row.computed_at.isoformat(),
        "parameters": row.parameters,
        "current_state": cs,
    }


@router.get("/regimes/{key}/timeseries")
@_limiter.limit("30/minute")
def get_timeseries(
    request: Request,
    key: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Return the full historical timeseries for a regime model."""
    row = _lookup_snapshot(db, key)
    return {
        "regime_type": row.regime_type,
        "computed_at": row.computed_at.isoformat(),
        "timeseries": row.timeseries,
    }


@router.get("/regimes/{key}/strategy")
@_limiter.limit("30/minute")
def get_strategy(
    request: Request,
    key: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Return strategy backtest results (only models with allocations)."""
    row = _lookup_snapshot(db, key)
    if row.strategy is None:
        raise HTTPException(
            status_code=404,
            detail=f"Regime '{key}' has no strategy data.",
        )
    return {
        "regime_type": row.regime_type,
        "computed_at": row.computed_at.isoformat(),
        "strategy": row.strategy,
    }


@router.get("/regimes/{key}/assets")
@_limiter.limit("30/minute")
def get_asset_analytics(
    request: Request,
    key: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Return per-regime asset analytics."""
    row = _lookup_snapshot(db, key)
    if row.asset_analytics is None:
        raise HTTPException(
            status_code=404,
            detail=f"Regime '{key}' has no asset analytics.",
        )
    return {
        "regime_type": row.regime_type,
        "computed_at": row.computed_at.isoformat(),
        "asset_analytics": row.asset_analytics,
    }


@router.get("/regimes/{key}/meta")
@_limiter.limit("60/minute")
def get_meta(
    request: Request,
    key: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Return model methodology documentation."""
    row = _lookup_snapshot(db, key)
    return {
        "regime_type": row.regime_type,
        "computed_at": row.computed_at.isoformat(),
        "meta": row.meta,
    }


# ─────────────────────────────────────────────────────────────────────
# Admin refresh
# ─────────────────────────────────────────────────────────────────────


def _run_refresh(key: str) -> None:
    """Background task runner."""
    try:
        fp = compute_regime(key)
        logger.info("Regime refresh complete: %s", fp)
    except Exception as exc:
        logger.exception("Regime refresh failed for %s: %s", key, exc)


@router.post("/regimes/{key}/refresh")
@_limiter.limit("5/minute")
def refresh_regime(
    request: Request,
    key: str,
    _user=Depends(get_current_admin_user),
):
    """Trigger a background recompute of a regime model (admin only)."""
    try:
        get_regime(key)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Regime '{key}' is not registered.",
        )

    _refresh_executor.submit(_run_refresh, key)
    return {"status": "computing", "regime": key}
