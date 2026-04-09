"""Regime model registry.

Central place where regime models register themselves.  The API router,
scheduler, and frontend all discover available regimes through this
registry — no hardcoding.

To add a new regime model:

    1. Create a subclass of :class:`ix.core.regimes.base.Regime`
    2. Register it here with ``register_regime(key, RegimeRegistration(...))``
    3. Done — API, DB, and frontend pick it up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type, Optional, Literal

from .base import Regime


# UI grouping / composability category:
#   "axis"  — single composite over N indicators (growth, inflation, liquidity).
#             Composable: 2+ axes can be cross-multiplied into a custom composite
#             on demand via the /api/regimes/compose endpoint.
#   "phase" — single signal decomposed into level × trend → 4 cycle states
#             (credit, dollar). Not composable — already 4-state from one concept.
#
# All built-in regimes are 1D. Multi-axis views (e.g. growth × inflation) are
# generated on the fly by the user-driven compose endpoint.
RegimeCategory = Literal["axis", "phase"]


# ─────────────────────────────────────────────────────────────────────
# Registration dataclass
# ─────────────────────────────────────────────────────────────────────


@dataclass
class RegimeRegistration:
    """Metadata for a registered regime model."""

    # Identity
    key: str                              # URL key: "growth", "inflation", "liquidity", ...
    display_name: str                     # UI label: "Growth (Expansion × Contraction)"
    description: str                      # Short tagline

    # Structure
    states: list[str]                     # e.g. ["Expansion", "Contraction"]
    dimensions: list[str]                 # e.g. ["Growth"]

    # Computation
    regime_class: Optional[Type[Regime]] = None
    computer_class: Optional[type] = None         # None → use generic RegimeComputer
    default_params: dict = field(default_factory=dict)

    # Capabilities
    has_strategy: bool = False            # Populates `strategy` column with backtest results

    # UI grouping + composability category. "axis" regimes can be combined
    # into custom multi-axis composites by the user (e.g. growth × inflation).
    category: RegimeCategory = "axis"

    # Structural phase pairing. When a single cycle is split into a
    # level regime and a trend regime (e.g. credit_level + credit_trend →
    # 4-state Verdad cycle, dollar_level + dollar_trend → 4-state dollar
    # cycle), set this to the sibling's key. The frontend and the
    # composition tooling can then auto-suggest "compose with your pair"
    # without relying on description text. ``None`` means no paired sibling.
    phase_pair: Optional[str] = None

    # Asset universe for per-regime performance analytics.
    # Mapping of display ticker → DB code. If None, defaults to a broad
    # macro universe (SPY, IWM, EFA, EEM, TLT, IEF, TIP, HYG, GLD, DBC, BIL).
    # Each regime should pick an asset universe that matches its signal —
    # e.g. credit cycle → HYG/LQD/EMB, dollar cycle → EEM/EFA/GLD.
    asset_tickers: Optional[dict[str, str]] = None

    # Presentation
    color_map: dict[str, str] = field(default_factory=dict)       # state → hex
    dimension_colors: dict[str, str] = field(default_factory=dict)
    # Per-state short descriptions for UI (e.g. "Growth accelerating — risk-on").
    # When two regimes share a state name (e.g. "Expansion" in both credit and
    # growth), state_descriptions disambiguates the tooltip shown in the UI.
    state_descriptions: dict[str, str] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, RegimeRegistration] = {}


def register_regime(reg: RegimeRegistration) -> None:
    """Register a regime model. Overwrites if key already exists."""
    _REGISTRY[reg.key] = reg


def get_regime(key: str) -> RegimeRegistration:
    """Look up a registered regime by key. Raises KeyError if missing."""
    if key not in _REGISTRY:
        raise KeyError(
            f"Regime '{key}' not registered. "
            f"Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[key]


def list_regimes() -> list[RegimeRegistration]:
    """Return all registered regimes in insertion order."""
    return list(_REGISTRY.values())


def get_phase_pair(key: str) -> Optional[RegimeRegistration]:
    """Return the paired sibling regime, if the given key has a ``phase_pair``.

    Example:
        ``get_phase_pair("credit_level")`` → the ``credit_trend`` registration.
        ``get_phase_pair("growth")``       → ``None``.

    Used by the frontend composition UI to auto-suggest "you probably want to
    compose with your pair" and by the composition validator to flag when a
    level regime is used without its matching trend regime.
    """
    reg = get_regime(key)
    if not reg.phase_pair:
        return None
    return _REGISTRY.get(reg.phase_pair)


# ─────────────────────────────────────────────────────────────────────
# Built-in registrations
# ─────────────────────────────────────────────────────────────────────

# Shared color palette
_LIQUIDITY_COLORS = {
    "Easing":     "#22c55e",
    "Tightening": "#ef5350",
}

_DIMENSION_COLORS = {
    "Growth":    "#22c55e",
    "Inflation": "#ef5350",
    "Liquidity": "#6382ff",
}

_DEFAULT_PARAMS = {
    "z_window": 96,      # 8 years — covers a full business cycle
    "sensitivity": 2.0,   # 2× decisiveness vs default 1.0
    "smooth_halflife": 2, # light smoothing — decisive enough to read, stable enough to trade
    "confirm_months": 3,
}


def _register_builtins() -> None:
    """Register the built-in regime models. Called at import time.

    All built-in regimes are 1D (single-dimension). Multi-axis composites
    are generated on demand by /api/regimes/compose from any combination
    of registered axis regimes.
    """
    from .flow.liquidity import LiquidityRegime
    from .markets.credit import CreditLevelRegime, CreditTrendRegime
    from .markets.dollar import DollarLevelRegime, DollarTrendRegime
    from .fundamentals.growth import GrowthRegime
    from .fundamentals.inflation import InflationRegime
    from .flow.yield_curve import YieldCurveRegime
    from .flow.real_rates import RealRatesRegime
    # New 1D regimes (2026-04) — see STANDARD.md for the build bar.
    from .risk.vol_term import VolatilityTermStructureRegime
    from .risk.breadth import BreadthRegime
    from .risk.earnings_revisions import EarningsRevisionsRegime
    from .risk.positioning import PositioningRegime
    from .risk.risk_appetite import RiskAppetiteRegime
    from .flow.liquidity_impulse import LiquidityImpulseRegime
    from .fundamentals.labor import LaborRegime
    from .markets.commodity_cycle import CommodityCycleRegime
    from .risk.dispersion import DispersionRegime
    from .fundamentals.cb_surprise import CBSurpriseRegime

    # 1. LiquidityRegime (2 states) — AXIS regime, composable
    # Rebuilt 2026-04-09 as a pure central-bank quantity regime (G4 balance
    # sheets, Fed net liquidity, TGA drawdown, credit impulse). Previous
    # version mixed HY/IG/DXY/curve signals that double-counted credit_level,
    # dollar_level and yield_curve.
    register_regime(RegimeRegistration(
        key="liquidity",
        display_name="Liquidity (Easing × Tightening)",
        description=(
            "2-state central-bank liquidity regime — G4 balance sheet YoY, "
            "Fed assets YoY, Fed net liquidity 3M, TGA drawdown, credit "
            "impulse. Target: SPY 3M fwd (0.60 vol-normalized spread). "
            "Pair with liquidity_impulse to reconstruct the full "
            "level × impulse cycle."
        ),
        states=["Easing", "Tightening"],
        dimensions=["Liquidity"],
        regime_class=LiquidityRegime,
        default_params={**_DEFAULT_PARAMS, "confirm_months": 2},
        has_strategy=False,
        category="axis",
        phase_pair="liquidity_impulse",
        color_map=_LIQUIDITY_COLORS.copy(),
        dimension_colors={"Liquidity": _DIMENSION_COLORS["Liquidity"]},
    ))

    # 5a. DollarLevelRegime (2-state Strong/Weak from absolute level)
    # AXIS regime — composable. Combine with `dollar_trend` to recreate
    # the original 4-state dollar cycle, or compose with growth/inflation
    # for cross-asset views.
    _DOLLAR_ASSET_TICKERS = {
        # Dollar-sensitive universe: EM-heavy, commodities, DM equity
        "EEM": "EEM US EQUITY:PX_LAST",   # EM equities (most dollar-sensitive)
        "EFA": "EFA US EQUITY:PX_LAST",   # Developed ex-US
        "SPY": "SPY US EQUITY:PX_LAST",   # US benchmark
        "GLD": "GLD US EQUITY:PX_LAST",   # Gold (inverse dollar)
        "DBC": "DBC US EQUITY:PX_LAST",   # Commodities (dollar-priced)
        "TLT": "TLT US EQUITY:PX_LAST",   # Long bonds
        "HYG": "HYG US EQUITY:PX_LAST",   # HY credit
        "BIL": "BIL US EQUITY:PX_LAST",   # Cash
    }
    register_regime(RegimeRegistration(
        key="dollar_level",
        display_name="Dollar Level (Strong × Weak)",
        description=(
            "2-state dollar level regime — z-score of DXY + Trade-Weighted "
            "USD baskets vs rolling 8y history. Target: EEM 6M fwd. "
            "Compose with dollar_trend to reconstruct the 4-state cycle."
        ),
        states=["Strong", "Weak"],
        dimensions=["Level"],
        regime_class=DollarLevelRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        phase_pair="dollar_trend",
        asset_tickers=_DOLLAR_ASSET_TICKERS,
        color_map={
            "Strong": "#ef5350",  # red — strong dollar = bearish for EM
            "Weak":   "#22c55e",  # green — weak dollar = bullish for EM
        },
        dimension_colors={"Level": "#ef5350"},
        state_descriptions={
            "Strong": "Dollar above rolling history — EM/commodity headwind",
            "Weak":   "Dollar below rolling history — EM/commodity tailwind",
        },
    ))

    # 5b. DollarTrendRegime (2-state Appreciating/Depreciating from 3M ROC)
    register_regime(RegimeRegistration(
        key="dollar_trend",
        display_name="Dollar Trend (Appreciating × Depreciating)",
        description=(
            "2-state dollar trend regime — 3M absolute change z-score of "
            "DXY + Trade-Weighted USD baskets. Target: EEM 6M fwd. "
            "Captures the turning-point signal — best paired with dollar_level."
        ),
        states=["Appreciating", "Depreciating"],
        dimensions=["Trend"],
        regime_class=DollarTrendRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        phase_pair="dollar_level",
        asset_tickers=_DOLLAR_ASSET_TICKERS,
        color_map={
            "Appreciating": "#ef5350",  # red — rising dollar
            "Depreciating": "#22c55e",  # green — falling dollar
        },
        dimension_colors={"Trend": "#f59e0b"},
        state_descriptions={
            "Appreciating": "Dollar rising over the last 3 months",
            "Depreciating": "Dollar falling over the last 3 months",
        },
    ))

    # 4a. CreditLevelRegime (2-state Wide/Tight from absolute spread level)
    # AXIS regime — composable. Combine with `credit_trend` to recreate
    # the original 4-state Verdad credit cycle, or compose with growth/
    # inflation/dollar for cross-asset views.
    _CREDIT_ASSET_TICKERS = {
        # Credit-sensitive universe: HY/IG credit + safe haven comparisons
        "HYG": "HYG US EQUITY:PX_LAST",   # HY credit (most sensitive)
        "LQD": "LQD US EQUITY:PX_LAST",   # IG credit
        "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (flight to quality)
        "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate Treasuries
        "SPY": "SPY US EQUITY:PX_LAST",   # Equity (credit-equity correlation)
        "GLD": "GLD US EQUITY:PX_LAST",   # Gold (crisis hedge)
        "BIL": "BIL US EQUITY:PX_LAST",   # Cash
    }
    register_regime(RegimeRegistration(
        key="credit_level",
        display_name="Credit Level (Wide × Tight)",
        description=(
            "2-state credit level regime — z-score of HY/IG/BBB OAS vs "
            "rolling 8y history. Target: HYG 6M fwd. "
            "Compose with credit_trend to reconstruct the Verdad cycle."
        ),
        states=["Wide", "Tight"],
        dimensions=["Level"],
        regime_class=CreditLevelRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        phase_pair="credit_trend",
        asset_tickers=_CREDIT_ASSET_TICKERS,
        color_map={
            "Wide":  "#ef5350",  # red — wide spreads = stress
            "Tight": "#22c55e",  # green — tight spreads = carry
        },
        dimension_colors={"Level": "#ef5350"},
        state_descriptions={
            "Wide":  "Spreads above rolling history — risk premium embedded",
            "Tight": "Spreads below rolling history — carry-friendly conditions",
        },
    ))

    # 4b. CreditTrendRegime (2-state Widening/Tightening from 3M ROC)
    register_regime(RegimeRegistration(
        key="credit_trend",
        display_name="Credit Trend (Widening × Tightening)",
        description=(
            "2-state credit trend regime — 3M absolute change z-score of "
            "HY/IG/BBB OAS. Target: HYG 6M fwd. "
            "Captures the turning-point signal — best paired with credit_level."
        ),
        states=["Widening", "Tightening"],
        dimensions=["Trend"],
        regime_class=CreditTrendRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        phase_pair="credit_level",
        asset_tickers=_CREDIT_ASSET_TICKERS,
        color_map={
            "Widening":   "#ef5350",  # red — spreads rising = stress
            "Tightening": "#22c55e",  # green — spreads falling = recovery
        },
        dimension_colors={"Trend": "#f59e0b"},
        state_descriptions={
            "Widening":   "Spreads rising over the last 3 months — credit stress building",
            "Tightening": "Spreads falling over the last 3 months — credit recovery",
        },
    ))

    # 6. GrowthRegime (2-state growth regime, decomposed from Macro)
    # TIER 1 5/6 PASS (spread 2.14% < 5 fails T1.4, all other mandatory bars pass).
    # Robustness 4/4 at SPY 3M: Welch p=0.009, perm p=0.003, sign-consistent,
    # spread > noise. Shipped as production despite tight spread because the
    # signal is robust against all "not luck" checks.
    register_regime(RegimeRegistration(
        key="growth",
        display_name="Growth (Expansion × Contraction)",
        description=(
            "2-state growth regime from the shared growth loader (8 indicators: "
            "claims, ISM new orders, OECD CLI, LEI, payrolls, CLI diffusion, "
            "permits, NO-Inv). Target: SPY 3M fwd, robust 4/4 on permutation + "
            "subsample stability tests."
        ),
        states=["Expansion", "Contraction"],
        dimensions=["Growth"],
        regime_class=GrowthRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers={
            # Growth-sensitive universe: cyclicals + defensives
            "SPY": "SPY US EQUITY:PX_LAST",   # US large cap
            "IWM": "IWM US EQUITY:PX_LAST",   # Small cap (most growth-sensitive)
            "EEM": "EEM US EQUITY:PX_LAST",   # EM (global growth proxy)
            "HYG": "HYG US EQUITY:PX_LAST",   # HY credit
            "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (defensive)
            "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate (defensive)
            "GLD": "GLD US EQUITY:PX_LAST",   # Gold (defensive)
            "BIL": "BIL US EQUITY:PX_LAST",   # Cash
        },
        color_map={
            "Expansion":   "#22c55e",   # green — growth positive
            "Contraction": "#ef5350",   # red — growth negative
        },
        dimension_colors={"Growth": _DIMENSION_COLORS["Growth"]},
        state_descriptions={
            "Expansion":   "Growth accelerating — ISM expanding, claims falling, LEI rising",
            "Contraction": "Growth decelerating — ISM contracting, claims rising, LEI falling",
        },
    ))

    # 7. InflationRegime (2-state inflation regime, decomposed from Macro)
    # TIER 1 6/6 PASS — spread +9.38% on WTI 6M fwd, p<0.001, perm p<0.001,
    # sign-consistent. Robustness 4/4. Note: "Falling" state is best for
    # commodity forward returns due to mean-reversion (same turning-point
    # pattern as credit/dollar/liquidity regimes).
    register_regime(RegimeRegistration(
        key="inflation",
        display_name="Inflation (Rising × Falling)",
        description=(
            "2-state inflation regime from the shared inflation loader (8 "
            "indicators: ISM prices, CPI 3M, breakeven, PCE core, median CPI, "
            "wages, WTI, commodities — all structural-anchored). Target: WTI "
            "6M fwd, robust 4/4. Best state = Falling (mean reversion)."
        ),
        states=["Rising", "Falling"],
        dimensions=["Inflation"],
        regime_class=InflationRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers={
            # Inflation-sensitive universe: commodities, real assets, TIPS
            "GLD": "GLD US EQUITY:PX_LAST",   # Gold
            "SLV": "SLV US EQUITY:PX_LAST",   # Silver
            "DBC": "DBC US EQUITY:PX_LAST",   # Broad commodities
            "DBA": "DBA US EQUITY:PX_LAST",   # Agriculture
            "TIP": "TIP US EQUITY:PX_LAST",   # TIPS
            "XLE": "XLE US EQUITY:PX_LAST",   # Energy equities
            "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (inverse)
            "SPY": "SPY US EQUITY:PX_LAST",   # Equity benchmark
            "BIL": "BIL US EQUITY:PX_LAST",   # Cash
        },
        color_map={
            "Rising":  "#ef5350",   # red — inflationary pressure
            "Falling": "#22c55e",   # green — disinflation
        },
        dimension_colors={"Inflation": _DIMENSION_COLORS["Inflation"]},
        state_descriptions={
            "Rising":  "Inflation accelerating — CPI above 2.5%, breakeven rising, wages hot",
            "Falling": "Inflation decelerating — CPI cooling, commodity prices receding",
        },
    ))

    # 8. YieldCurveRegime (2-state slope regime, Steep × Flat)
    # TIER 1 6/6 PASS — spread +6.37% on SPY 12M fwd, p=0.0003, perm p=0.001,
    # sign-consistent across 2010 split. Robustness 4/4. Custom z_window=60 (5y)
    # matches the FCI-regime convention. Best state = Flat (mean reversion —
    # same contrarian turning-point pattern as credit/dollar/inflation).
    register_regime(RegimeRegistration(
        key="yield_curve",
        display_name="Yield Curve (Steep × Flat)",
        description=(
            "2-state yield-curve slope regime — pure level z-score of "
            "3m10y, 2s10s, 5s30s Treasury slopes vs rolling 5y history. "
            "Estrella & Mishkin canonical recession leading indicator. "
            "Target: SPY 12M fwd, Tier 1 6/6 (spread +6.37%, p<0.001). "
            "Best state = Flat (post-inversion recovery rally)."
        ),
        states=["Steep", "Flat"],
        dimensions=["YieldCurve"],
        regime_class=YieldCurveRegime,
        default_params={
            "z_window": 60,        # 5y — FCI-regime convention
            "sensitivity": 2.0,
            "smooth_halflife": 2,
            "confirm_months": 3,
        },
        has_strategy=False,
        category="axis",
        asset_tickers={
            # Yield-curve sensitive: cyclicals + duration + safe haven
            "SPY": "SPY US EQUITY:PX_LAST",   # US large cap (locked target)
            "IWM": "IWM US EQUITY:PX_LAST",   # Small cap (most cyclical)
            "EEM": "EEM US EQUITY:PX_LAST",   # EM (recession-sensitive)
            "HYG": "HYG US EQUITY:PX_LAST",   # HY credit (cyclical credit)
            "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (duration)
            "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate (duration)
            "GLD": "GLD US EQUITY:PX_LAST",   # Gold (recession hedge)
            "BIL": "BIL US EQUITY:PX_LAST",   # Cash
        },
        color_map={
            "Steep": "#22c55e",  # green — steep curve = expansionary
            "Flat":  "#ef5350",  # red — flat/inverted = late-cycle / recession warning
        },
        dimension_colors={"YieldCurve": "#6382ff"},
        state_descriptions={
            "Steep": "Slope above rolling 5y history — expansionary stance, normal carry",
            "Flat":  "Slope below rolling 5y history — late-cycle, restrictive, recession warning",
        },
    ))

    # 9. RealRatesRegime (2-state real interest rate level, High × Low)
    # TIER 2 FULL PASS on iteration 1 — spread +14.45% on GC1 COMDTY 12M fwd,
    # p<0.0001, Cohen's d +0.888, DD avoidance 80.6%, OOS stable (+5.63/+20.28
    # sign-consistent). 4 indicators blended: TIPS 10Y/5Y (post-2003), Cleveland
    # Fed HPR 1Y (post-1982), synthetic 10Y (nominal − CPI YoY, post-1954).
    # Same contrarian turning-point pattern as credit/dollar/yield curve: High
    # real rates today → Fed pivot → real rate drop → gold rally 12M forward.
    register_regime(RegimeRegistration(
        key="real_rates",
        display_name="Real Rates (High × Low)",
        description=(
            "2-state real interest rate level regime — pure level z-score of "
            "TIPS 10Y/5Y, Cleveland Fed 1Y real rate, and synthetic 10Y "
            "(nominal − CPI YoY) vs rolling 8y history. Target: GC1 COMDTY "
            "12M fwd, Tier 2 5/5 (spread +14.45%, p<0.0001, d=0.888). "
            "Best state = High (contrarian turning point — restrictive real "
            "rates precede Fed pivot → real rate drop → gold rally)."
        ),
        states=["High", "Low"],
        dimensions=["RealRates"],
        regime_class=RealRatesRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers={
            # Real-rate-sensitive universe: gold, duration, TIPS, inflation hedges
            "GLD": "GLD US EQUITY:PX_LAST",   # Gold (locked target proxy)
            "SLV": "SLV US EQUITY:PX_LAST",   # Silver
            "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (duration)
            "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate Treasuries
            "TIP": "TIP US EQUITY:PX_LAST",   # TIPS (real yield direct)
            "SPY": "SPY US EQUITY:PX_LAST",   # US equity (P/E sensitivity)
            "XLU": "XLU US EQUITY:PX_LAST",   # Utilities (duration proxy)
            "BIL": "BIL US EQUITY:PX_LAST",   # Cash
        },
        color_map={
            "High": "#ef5350",  # red — restrictive real rates (contemporaneous headwind)
            "Low":  "#22c55e",  # green — accommodative real rates (contemporaneous tailwind)
        },
        dimension_colors={"RealRates": "#f59e0b"},
        state_descriptions={
            "High": "Real rates above rolling 8y history — restrictive Fed stance, late-tightening cycle. Contrarian setup: precedes Fed pivot → real rate drop → gold rally 12M fwd.",
            "Low":  "Real rates below rolling 8y history — accommodative Fed stance, mid-easing cycle. Post-rally consolidation: gold has already repriced, limited further forward upside.",
        },
    ))

    # ─────────────────────────────────────────────────────────────────
    # New 1D regimes (2026-04 cohort)
    # ─────────────────────────────────────────────────────────────────
    #
    # All 10 follow STANDARD.md. Each is category="axis" (composable),
    # default_params match the existing 8y cycle window, and color_map
    # uses the steel palette for consistency with the redesigned macro
    # page. Asset universes are chosen per-signal.
    #
    # Data availability at the time of registration is mixed — some
    # regimes will show 0 indicators until the underlying series are
    # seeded. This is the documented "draft" state; the regime is still
    # registered so the frontend surfaces it and the Decision Card D4
    # gate correctly fails when data is missing.
    # ─────────────────────────────────────────────────────────────────

    _MACRO_ASSET_TICKERS = {
        "SPY": "SPY US EQUITY:PX_LAST",
        "IWM": "IWM US EQUITY:PX_LAST",
        "EEM": "EEM US EQUITY:PX_LAST",
        "HYG": "HYG US EQUITY:PX_LAST",
        "TLT": "TLT US EQUITY:PX_LAST",
        "IEF": "IEF US EQUITY:PX_LAST",
        "GLD": "GLD US EQUITY:PX_LAST",
        "BIL": "BIL US EQUITY:PX_LAST",
    }

    _COMMODITY_ASSET_TICKERS = {
        "DBC": "DBC US EQUITY:PX_LAST",
        "DBA": "DBA US EQUITY:PX_LAST",
        "GLD": "GLD US EQUITY:PX_LAST",
        "SLV": "SLV US EQUITY:PX_LAST",
        "XLE": "XLE US EQUITY:PX_LAST",
        "XLB": "XLB US EQUITY:PX_LAST",
        "SPY": "SPY US EQUITY:PX_LAST",
        "BIL": "BIL US EQUITY:PX_LAST",
    }

    # 10. VolatilityTermStructureRegime — VIX curve shape
    register_regime(RegimeRegistration(
        key="vol_term",
        display_name="Vol Term (Complacent × Stressed)",
        description=(
            "2-state VIX term-structure regime — z-score of VIX3M/VIX ratio + "
            "3M change + VIX-realized spread. Target: SPY 3M fwd. Contrarian "
            "mapping at backwardation extreme. Draft — needs VIX3M seeded."
        ),
        states=["Complacent", "Stressed"],
        dimensions=["VolTerm"],
        regime_class=VolatilityTermStructureRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Complacent": "#E0A848",  # amber — warning, not actionable
            "Stressed":   "#48A86E",  # steel green — contrarian buy signal
        },
        dimension_colors={"VolTerm": "#E0A848"},
        state_descriptions={
            "Complacent": "Deep contango — options market relaxed. Below-average forward returns (grinding-up or topping).",
            "Stressed":   "Backwardation — near-term vol premium. Historically above-average forward 3m returns (mean reversion).",
        },
    ))

    # 11. BreadthRegime — equity market internals
    register_regime(RegimeRegistration(
        key="breadth",
        display_name="Breadth (Broad × Narrow)",
        description=(
            "2-state equity market breadth regime — z-score of % above "
            "200DMA, % above 50DMA, McClellan Oscillator, NH-NL spread. "
            "Target: SPY 3M fwd. Orthogonal to all macro axes. Draft — "
            "needs S5TH / S5FI / MCOS / NHIGH / NLOW seeded."
        ),
        states=["Broad", "Narrow"],
        dimensions=["Breadth"],
        regime_class=BreadthRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Broad":  "#48A86E",
            "Narrow": "#D65656",
        },
        dimension_colors={"Breadth": "#4895B0"},
        state_descriptions={
            "Broad":  "Wide participation — majority of index above 200DMA, McClellan positive. Healthy trend.",
            "Narrow": "Thin participation — distribution or washout. Negative forward returns on avg; contrarian at washout extreme.",
        },
    ))

    # 12. EarningsRevisionsRegime — bottom-up fundamentals
    register_regime(RegimeRegistration(
        key="earnings_revisions",
        display_name="Earnings Revisions (Accelerating × Decelerating)",
        description=(
            "2-state earnings revision breadth regime — z-score of Revision "
            "Breadth Index + 3M forward EPS change + guidance spread. Target: "
            "SPY 3M fwd, coincident. Leads macro Growth axis by 1-2 months at "
            "turning points. Draft — needs IBES / FactSet feed."
        ),
        states=["Accelerating", "Decelerating"],
        dimensions=["Revisions"],
        regime_class=EarningsRevisionsRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Accelerating": "#48A86E",
            "Decelerating": "#D65656",
        },
        dimension_colors={"Revisions": "#48A86E"},
        state_descriptions={
            "Accelerating": "Revision breadth positive — upgrades outnumber downgrades. Earnings momentum improving.",
            "Decelerating": "Revision breadth negative — downgrades dominate. Earnings momentum failing, forward returns weak.",
        },
    ))

    # 13. PositioningRegime — contrarian crowd gauge (3 states)
    register_regime(RegimeRegistration(
        key="positioning",
        display_name="Positioning (Extreme Long × Neutral × Capitulation)",
        description=(
            "3-state contrarian positioning regime — blended z-score of CFTC "
            "asset manager net long, NAAIM exposure, AAII bull-bear, NYSE "
            "margin debt YoY. Target: SPY 3M fwd. Signal only fires at the "
            "tails (|z| > 1). Contrarian mapping: Capitulation state is "
            "historically the highest-return state."
        ),
        states=["ExtremeLong", "Neutral", "Capitulation"],
        dimensions=["Positioning"],
        regime_class=PositioningRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "ExtremeLong":  "#D65656",  # red — contrarian bearish
            "Neutral":      "#7D8596",  # slate — no signal
            "Capitulation": "#48A86E",  # green — contrarian bullish
        },
        dimension_colors={"Positioning": "#E0A848"},
        state_descriptions={
            "ExtremeLong":  "Crowded long (> +1σ composite). Contrarian bearish setup — forward returns below average.",
            "Neutral":      "Normal positioning — no tradeable signal from this axis.",
            "Capitulation": "Crowded short / capitulated (< −1σ composite). Contrarian bullish — historically the strongest forward return state.",
        },
    ))

    # 14. RiskAppetiteRegime — cross-asset risk gauge
    register_regime(RegimeRegistration(
        key="risk_appetite",
        display_name="Risk Appetite (Risk-On × Risk-Off)",
        description=(
            "2-state cross-asset risk appetite regime — joint z-score of HY "
            "spread change, MOVE, DXY change, copper/gold ratio, EM FX basket. "
            "Insists all 5 agree. Target: SPY 3M fwd, coincident. Orthogonality "
            "vs Credit-Trend + Dollar-Trend must be re-verified post-build."
        ),
        states=["RiskOn", "RiskOff"],
        dimensions=["Risk"],
        regime_class=RiskAppetiteRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "RiskOn":  "#48A86E",
            "RiskOff": "#D65656",
        },
        dimension_colors={"Risk": "#4895B0"},
        state_descriptions={
            "RiskOn":  "HY tightening, MOVE low, dollar weak, copper > gold, EM FX firm. Broad cross-asset appetite.",
            "RiskOff": "HY widening, MOVE high, dollar strong, gold > copper, EM FX stressed. Broad risk-off.",
        },
    ))

    # 15. LiquidityImpulseRegime — US quantity-based liquidity
    register_regime(RegimeRegistration(
        key="liquidity_impulse",
        display_name="Liquidity Impulse (Expanding × Contracting)",
        description=(
            "2-state US liquidity quantity regime — 3M change in Fed balance "
            "sheet, TGA (inverted), RRP (inverted), and net liquidity "
            "aggregate. US-specific, not Global M2. Target: SPY 3M fwd. "
            "Paired with `liquidity` (level) to capture the full level × "
            "impulse cycle."
        ),
        states=["Expanding", "Contracting"],
        dimensions=["Impulse"],
        regime_class=LiquidityImpulseRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        phase_pair="liquidity",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Expanding":   "#48A86E",
            "Contracting": "#D65656",
        },
        dimension_colors={"Impulse": "#4895B0"},
        state_descriptions={
            "Expanding":   "Net liquidity rising over 3M — TGA drawing down, RRP unwinding, or Fed BS growing. Tailwind for risk.",
            "Contracting": "Net liquidity falling over 3M — TGA rebuilding, RRP growing, or BS shrinking. Headwind for risk.",
        },
    ))

    # 16. LaborRegime — Sahm rule + claims trend
    register_regime(RegimeRegistration(
        key="labor",
        display_name="Labor (Tight × Deteriorating)",
        description=(
            "2-state labor market cycle regime — z-score of 4w claims MA, "
            "Sahm rule proxy, unemployment level, and labor force "
            "participation. Target: SPY 3M fwd. Slow axis intended for "
            "gating faster signals near cycle tops. 100% hit rate on NBER "
            "recessions since 1950."
        ),
        states=["Tight", "Deteriorating"],
        dimensions=["Labor"],
        regime_class=LaborRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Tight":         "#48A86E",
            "Deteriorating": "#D65656",
        },
        dimension_colors={"Labor": "#48A86E"},
        state_descriptions={
            "Tight":         "Claims low, unemployment low, Sahm = 0, LFPR rising. Peak-cycle labor conditions.",
            "Deteriorating": "Claims rising, unemployment rising, Sahm rule triggered. Recession window — forward returns sharply negative historically.",
        },
    ))

    # 17. CommodityCycleRegime — industrial commodities
    register_regime(RegimeRegistration(
        key="commodity_cycle",
        display_name="Commodity Cycle (Reflation × Deflation)",
        description=(
            "2-state industrial commodity cycle regime — z-score of copper/"
            "gold ratio 6M momentum, WTI 12-1 momentum, industrial metals "
            "index vs 200DMA. Target: SPY 3M fwd, coincident. Cyclical "
            "leadership indicator — overlaps partially with Inflation (WTI) "
            "and Dollar-Trend."
        ),
        states=["Reflation", "Deflation"],
        dimensions=["Commodity"],
        regime_class=CommodityCycleRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_COMMODITY_ASSET_TICKERS,
        color_map={
            "Reflation": "#48A86E",
            "Deflation": "#D65656",
        },
        dimension_colors={"Commodity": "#B89176"},
        state_descriptions={
            "Reflation": "Copper > gold momentum, oil trending up, industrial metals above 200DMA. Global cyclical expansion.",
            "Deflation": "Cyclical commodities rolling over, defensive leadership, metals below 200DMA. Global demand weakening.",
        },
    ))

    # 18. DispersionRegime — cross-sectional strategy selector (3 states)
    register_regime(RegimeRegistration(
        key="dispersion",
        display_name="Dispersion (Macro × Stock-Picking × Crisis)",
        description=(
            "3-state cross-sectional dispersion regime — z-score of SPX "
            "constituent dispersion, CBOE implied correlation (inverted), "
            "and sector-spread breadth. Primarily a STRATEGY-SELECTION "
            "signal (index beta vs single-name rotation), directional only "
            "at the Crisis extreme. Orthogonal to all macro axes."
        ),
        states=["MacroDriven", "StockPicking", "Crisis"],
        dimensions=["Dispersion"],
        regime_class=DispersionRegime,
        default_params=_DEFAULT_PARAMS.copy(),
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "MacroDriven":  "#7D8596",  # slate — macro dominates, no stock picking
            "StockPicking": "#48A86E",  # green — rotation opportunities
            "Crisis":       "#D65656",  # red — high corr + high disp = tail
        },
        dimension_colors={"Dispersion": "#6B8EAE"},
        state_descriptions={
            "MacroDriven":  "Low dispersion, high correlation — everything moves together. Index beta dominates; stock-picking futile.",
            "StockPicking": "High dispersion, normal correlation — rotation opportunities. Single-name / sector selection pays.",
            "Crisis":       "High dispersion AND high correlation — rare tail state (DotCom top, 2008, 2020-Mar). Sharply negative forward returns.",
        },
    ))

    # 19. CBSurpriseRegime — short-horizon policy surprise (3 states)
    register_regime(RegimeRegistration(
        key="cb_surprise",
        display_name="CB Surprise (Dovish × Neutral × Hawkish)",
        description=(
            "3-state central bank policy surprise regime — z-score of "
            "30-day change in 1y OIS, 2y OIS, and terminal rate spread. "
            "Shortest-horizon regime in the registry. Target: SPY 1M fwd. "
            "Fast-decaying signal, best paired with slower axes."
        ),
        states=["Dovish", "Neutral", "Hawkish"],
        dimensions=["CBSurprise"],
        regime_class=CBSurpriseRegime,
        default_params={
            "z_window": 60,    # 5y — policy regimes are shorter
            "sensitivity": 2.0,
            "smooth_halflife": 1,  # minimal smoothing — signal is fast
            "confirm_months": 1,
        },
        has_strategy=False,
        category="axis",
        asset_tickers=_MACRO_ASSET_TICKERS,
        color_map={
            "Dovish":  "#48A86E",
            "Neutral": "#7D8596",
            "Hawkish": "#D65656",
        },
        dimension_colors={"CBSurprise": "#E0A848"},
        state_descriptions={
            "Dovish":  "OIS path has moved LOWER than expected over 30 days — yields falling more than priced. Tailwind for equities 1M fwd.",
            "Neutral": "OIS in line with pre-meeting expectations — no surprise signal.",
            "Hawkish": "OIS path has moved HIGHER than expected — yields rising more than priced. Headwind for equities 1M fwd.",
        },
    ))


_register_builtins()
