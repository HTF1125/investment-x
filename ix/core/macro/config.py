"""Constants and target index definitions for the macro outlook model.

This module contains all configuration that drives the three-horizon framework:
  1. Long-term: Global Liquidity Cycle
  2. Medium-term: Bayesian Growth x Inflation Regime Probabilities
  3. Short-term: Tactical Momentum & Positioning

Regimes (Growth x Inflation, standard macro quadrants):
  - Goldilocks:  Growth accelerating + Inflation decelerating
  - Reflation:   Growth accelerating + Inflation accelerating
  - Stagflation: Growth decelerating + Inflation accelerating
  - Deflation:   Growth decelerating + Inflation decelerating
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ix.db.custom import FinancialConditionsKR, FinancialConditionsIndexUS


# ==============================================================================
# TARGET INDEX DEFINITIONS
# ==============================================================================


@dataclass
class TargetIndex:
    """Metadata for a tradeable equity index used as backtest target."""

    name: str
    ticker: str
    region: str
    currency: str = ""
    bond_10y: str = ""
    fci_fn: Optional[callable] = None
    has_sectors: bool = False


TARGET_INDICES = {
    "MSCI ACWI": TargetIndex(
        "MSCI ACWI",
        "ACWI US EQUITY:PX_LAST",
        "global",
        currency="DXY INDEX:PX_LAST",
    ),
    "KOSPI": TargetIndex(
        "KOSPI",
        "KOSPI INDEX:PX_LAST",
        "korea",
        currency="USDKRW CURNCY:PX_LAST",
        bond_10y="TRYKR10Y:PX_YTM",
        fci_fn=FinancialConditionsKR,
        has_sectors=True,
    ),
    "S&P 500": TargetIndex(
        "S&P 500",
        "SPX INDEX:PX_LAST",
        "us",
        currency="DXY INDEX:PX_LAST",
        bond_10y="TRYUS10Y:PX_YTM",
        fci_fn=FinancialConditionsIndexUS,
        has_sectors=True,
    ),
    "Nasdaq 100": TargetIndex(
        "Nasdaq 100",
        "CCMP INDEX:PX_LAST",
        "us",
        currency="DXY INDEX:PX_LAST",
        bond_10y="TRYUS10Y:PX_YTM",
        fci_fn=FinancialConditionsIndexUS,
        has_sectors=True,
    ),
    "Nikkei 225": TargetIndex(
        "Nikkei 225",
        "NKY INDEX:PX_LAST",
        "japan",
        currency="USDJPY CURNCY:PX_LAST",
        bond_10y="TRYJP10Y:PX_YTM",
    ),
    "Euro Stoxx 50": TargetIndex(
        "Euro Stoxx 50",
        "SX5E INDEX:PX_LAST",
        "europe",
        currency="EURUSD CURNCY:PX_LAST",
        bond_10y="TRYDE10Y:PX_YTM",
    ),
    "MSCI EM": TargetIndex(
        "MSCI EM",
        "891800:FG_TOTAL_RET_IDX",
        "em",
        currency="DXY INDEX:PX_LAST",
    ),
    "Shanghai Composite": TargetIndex(
        "Shanghai Composite",
        "SHCOMP INDEX:PX_LAST",
        "china",
        currency="USDCNY CURNCY:PX_LAST",
    ),
    "DAX": TargetIndex(
        "DAX",
        "DAX INDEX:PX_LAST",
        "europe",
        currency="EURUSD CURNCY:PX_LAST",
        bond_10y="TRYDE10Y:PX_YTM",
    ),
    "FTSE 100": TargetIndex(
        "FTSE 100",
        "UKX INDEX:PX_LAST",
        "europe",
        currency="GBPUSD CURNCY:PX_LAST",
        bond_10y="TRYGB10Y:PX_YTM",
    ),
    "Hang Seng": TargetIndex(
        "Hang Seng",
        "HSI INDEX:PX_LAST",
        "china",
        currency="USDHKD CURNCY:PX_LAST",
    ),
    "KOSDAQ": TargetIndex(
        "KOSDAQ",
        "KOSDAQ:PX_LAST",
        "korea",
        currency="USDKRW CURNCY:PX_LAST",
        bond_10y="TRYKR10Y:PX_YTM",
        fci_fn=FinancialConditionsKR,
        has_sectors=True,
    ),
    "Gold": TargetIndex(
        "Gold",
        "IAU US EQUITY:PX_LAST",
        "global",
        currency="DXY INDEX:PX_LAST",
    ),
}


# ==============================================================================
# REGIME CONSTANTS
# ==============================================================================

REGIME_NAMES = ["Goldilocks", "Reflation", "Stagflation", "Deflation"]

# Centroids in (growth_z, inflation_z) space
REGIME_CENTROIDS = {
    "Goldilocks": np.array([+1.0, -1.0]),
    "Reflation": np.array([+1.0, +1.0]),
    "Stagflation": np.array([-1.0, +1.0]),
    "Deflation": np.array([-1.0, -1.0]),
}

# Historical return assumptions by regime (annualized, approximate)
REGIME_RETURN_ASSUMPTIONS = {
    "Goldilocks": 0.15,  # 15% annualized
    "Reflation": 0.10,  # 10%
    "Stagflation": -0.05,  # -5%
    "Deflation": 0.03,  # 3%
}


# ==============================================================================
# LIQUIDITY CYCLE CONSTANTS
# ==============================================================================

LIQUIDITY_PHASES = ["Spring", "Summer", "Fall", "Winter"]

LIQUIDITY_PHASE_BIAS = {
    "Spring": +0.05,  # Turning up from trough -- constructive
    "Summer": +0.10,  # Peak liquidity -- risk-on
    "Fall": -0.05,  # Decelerating -- caution
    "Winter": -0.10,  # Trough -- defensive
}
