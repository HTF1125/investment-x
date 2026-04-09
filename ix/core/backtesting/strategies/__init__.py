"""Concrete strategy implementations with discovery registry."""

from __future__ import annotations
from typing import Optional

# Active research strategies (one per file)
from .defense_first import SB_Carlson_DefenseFirst  # noqa: F401
from .gtaa import SB_Faber_GTAA5  # noqa: F401
from .baa import SB_Keller_BAABalanced  # noqa: F401
from .cdm import SB_Antonacci_CDM  # noqa: F401
from .macro_trend import SB_Consensus_MacroTrend  # noqa: F401
from .credit_cycle import SB_Auto_CreditCycle  # noqa: F401
from .vol_regime import SB_Auto_VolRegime  # noqa: F401
from .ensemble_trend import SB_Auto_EnsembleTrend  # noqa: F401
from .dollar_cycle import SB_Auto_DollarCycle  # noqa: F401
from .portfolio_ortho import SB_Portfolio_Top3Ortho  # noqa: F401
from .macro_regime import SB_Macro_GrowthInflation  # noqa: F401

# Archived (kept for reference)
from ._archive import (  # noqa: F401
    UsGicsEarningsImpulse, SectorRotationMom90, SectorRotationCESI,
    UsIsmPmiManuEB, UsOecdLeiEB, UsOecdLeiEB2, MAM60CF, SPX_Earnings,
    Classic6040, AllWeather, GoldenButterfly,
)


# ── Strategy Registry ────────────────────────────────────────────


STRATEGY_REGISTRY: dict[str, type] = {
    "SB_Carlson_DefenseFirst": SB_Carlson_DefenseFirst,
    "SB_Faber_GTAA5": SB_Faber_GTAA5,
    "SB_Keller_BAABalanced": SB_Keller_BAABalanced,
    "SB_Antonacci_CDM": SB_Antonacci_CDM,
    "SB_Consensus_MacroTrend": SB_Consensus_MacroTrend,
    "SB_Auto_CreditCycle": SB_Auto_CreditCycle,
    "SB_Auto_VolRegime": SB_Auto_VolRegime,
    "SB_Auto_EnsembleTrend": SB_Auto_EnsembleTrend,
    "SB_Auto_DollarCycle": SB_Auto_DollarCycle,
    "SB_Portfolio_Top3Ortho": SB_Portfolio_Top3Ortho,
    "SB_Macro_GrowthInflation": SB_Macro_GrowthInflation,
    "UsGicsEarningsImpulse": UsGicsEarningsImpulse,
    "SectorRotationMom90": SectorRotationMom90,
    "SectorRotationCESI": SectorRotationCESI,
    "UsIsmPmiManuEB": UsIsmPmiManuEB,
    "UsOecdLeiEB": UsOecdLeiEB,
    "UsOecdLeiEB2": UsOecdLeiEB2,
    "MAM60CF": MAM60CF,
    "SPX_Earnings": SPX_Earnings,
    "Classic6040": Classic6040,
    "AllWeather": AllWeather,
    "GoldenButterfly": GoldenButterfly,
}

STRATEGY_META: dict[str, dict] = {
    "SB_Carlson_DefenseFirst": {"family": "defensive", "mode": "replicate", "sharpe": 0.69, "active": True},
    "SB_Faber_GTAA5":         {"family": "trend", "mode": "replicate", "sharpe": 0.49, "active": True},
    "SB_Keller_BAABalanced":  {"family": "momentum", "mode": "replicate", "sharpe": 0.76, "active": True},
    "SB_Antonacci_CDM":       {"family": "momentum", "mode": "replicate", "sharpe": 0.51, "active": True},
    "SB_Consensus_MacroTrend": {"family": "macro", "mode": "synthesize", "sharpe": 0.80, "active": True},
    "SB_Auto_CreditCycle":    {"family": "credit", "mode": "auto", "sharpe": 0.92, "active": True},
    "SB_Auto_VolRegime":      {"family": "volatility", "mode": "auto", "sharpe": 0.66, "active": True},
    "SB_Auto_EnsembleTrend":  {"family": "trend", "mode": "auto", "sharpe": 0.55, "active": True},
    "SB_Auto_DollarCycle":    {"family": "dollar", "mode": "auto", "sharpe": 0.78, "active": True},
    "SB_Portfolio_Top3Ortho":    {"family": "ensemble", "mode": "ensemble", "sharpe": 1.01, "active": True},
    "SB_Macro_GrowthInflation": {"family": "macro", "mode": "synthesize", "sharpe": None, "active": True},
    "UsGicsEarningsImpulse":     {"family": "sector", "mode": "legacy", "active": False},
    "SectorRotationMom90":    {"family": "sector", "mode": "legacy", "active": False},
    "SectorRotationCESI":     {"family": "sector", "mode": "legacy", "active": False},
    "UsIsmPmiManuEB":         {"family": "macro", "mode": "legacy", "active": False},
    "UsOecdLeiEB":            {"family": "macro", "mode": "legacy", "active": False},
    "UsOecdLeiEB2":           {"family": "macro", "mode": "legacy", "active": False},
    "MAM60CF":                {"family": "macro", "mode": "legacy", "active": False},
    "SPX_Earnings":           {"family": "earnings", "mode": "legacy", "active": False},
    "Classic6040":            {"family": "static", "mode": "benchmark", "active": False},
    "AllWeather":             {"family": "static", "mode": "benchmark", "active": False},
    "GoldenButterfly":        {"family": "static", "mode": "benchmark", "active": False},
}


def get_strategy(name: str) -> type:
    """Get a strategy class by name."""
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy: {name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]


def list_strategies(
    active_only: bool = True,
    family: Optional[str] = None,
    mode: Optional[str] = None,
) -> list[str]:
    """List strategy names, optionally filtered by family or mode."""
    names = []
    for name, meta in STRATEGY_META.items():
        if active_only and not meta.get("active", True):
            continue
        if family and meta.get("family") != family:
            continue
        if mode and meta.get("mode") != mode:
            continue
        names.append(name)
    return names


def all_strategies() -> list[type]:
    """Return active strategy classes for scheduled backtesting."""
    return [STRATEGY_REGISTRY[n] for n in list_strategies(active_only=True)]


def get_strategy_meta(name: str) -> dict:
    """Get combined metadata from class attributes and STRATEGY_META."""
    cls = get_strategy(name)
    meta = STRATEGY_META.get(name, {}).copy()
    for attr in ("label", "family", "mode", "description", "author"):
        val = getattr(cls, attr, "")
        if val:
            meta[attr] = val
    return meta
