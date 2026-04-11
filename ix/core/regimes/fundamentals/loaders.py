"""Shared growth / inflation indicator loaders.

Extracted from the old 2D ``MacroRegime`` so that :class:`GrowthRegime` and
:class:`InflationRegime` can share the same indicator definitions without
carrying the deprecated 2-axis wrapper class.

Both loaders return ``{prefixed_name: z-scored series}`` dicts keyed with
``g_*`` (growth) and ``i_*`` (inflation) prefixes. Indicators use a
25% level z-score + 75% ROC z-score blend. Inflation indicators use
structural anchors (2.5% CPI, 0% commodities) instead of rolling means
so cycle regime reads are stable through disinflation eras.

Indicators
----------
Growth (2 composite, 2 monitor-only)
    g_LEI · g_CLIDiffusion
    m_ISMServices (monitor-only)
    g_Claims4WMA (loaded but excluded from composite)
    Dropped (IC decomposition 2026-04-10):
        g_InitialClaims (post IC -0.070), g_Payrolls (post IC -0.015),
        g_Permits (post IC -0.023), g_ISMNewOrders, g_OECDCLI, g_ISM_NO_Inv

Inflation (2)
    i_Breakeven (anchor 2.5%) · i_Commodities (anchor 0%)
    Dropped (IC decomposition 2026-04-10):
        i_ISMPricesPaid (post IC -0.026), i_WTI (post IC -0.036),
        i_PCECore (pre IC -0.040), i_Wages (pre IC -0.038),
        i_CPI3MAnn, i_MedianCPI
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import (
    load_series,
    zscore,
    zscore_ism,
    zscore_anchored,
    zscore_roc,
    LW,
    RW,
)

# Structural inflation anchors
INFLATION_ANCHOR = 2.5  # Fed target (2% target + small buffer) for CPI/PCE/breakeven
WAGE_ANCHOR = 3.5       # Productivity (~1.5%) + inflation target (~2%) ≈ wage equilibrium
COMMODITY_ANCHOR = 0.0  # 0% YoY = no commodity inflation pulse

log = logging.getLogger(__name__)

# Columns loaded for display but excluded from the composite z-score.
GROWTH_EXCLUDE_FROM_COMPOSITE: set[str] = {"g_Claims4WMA"}


def load_growth_indicators(z_window: int) -> dict[str, pd.Series]:
    """Load the ``g_*`` growth indicator set.

    Returns a dict of z-scored series keyed by ``g_*`` (composite) and
    ``m_*`` (monitor-only) names. Caller decides which prefixes enter the
    composite via its ``_dimension_prefixes`` / ``_exclude_from_composite``.
    """
    from ix.db.query import Series as DbSeries

    rows: dict[str, pd.Series] = {}

    # [DROPPED from composite: g_InitialClaims — post IC -0.070 (DYING).
    #  Positive full IC +0.025 but sign-flipped post-2010. Claims data
    #  is still loaded as monitor-only via g_Claims4WMA below.]
    ic_weekly_raw = DbSeries("ICSA")

    # Claims 4WMA nowcast — monitor-only, excluded from composite
    ic = (
        ic_weekly_raw.resample("ME").last()
        if not ic_weekly_raw.empty
        else pd.Series(dtype=float)
    )
    if not ic.empty:
        try:
            ic_4wma = -ic_weekly_raw.rolling(4, min_periods=2).mean()
            ic_4wma_m = ic_4wma.resample("ME").last()
            rows["g_Claims4WMA"] = zscore(ic_4wma_m, z_window).rename(
                "g_Claims4WMA"
            )
        except Exception as exc:
            log.warning("Claims 4WMA nowcast failed: %s", exc)

    lei = load_series("USSLIND", lag=1)
    if not lei.empty:
        rows["g_LEI"] = (
            zscore(lei, z_window) * LW
            + zscore_roc(lei, z_window, use_pct=True) * RW
        ).rename("g_LEI")

    # [DROPPED: g_Payrolls — post IC -0.015 (DYING). Full IC +0.051 but
    #  sign-flipped post-2010. Payrolls YoY is too lagging in modern
    #  cycle — labor data is covered by the dedicated LaborRegime.]

    # ISM Services — monitor only (m_ prefix)
    ism_svc = load_series("ISMNMI_NM:PX_LAST", lag=1)
    if ism_svc.empty:
        ism_svc = load_series("UMCSENT", lag=1)
    if not ism_svc.empty:
        rows["m_ISMServices"] = (
            zscore_ism(ism_svc, z_window) * LW
            + zscore_roc(ism_svc, z_window, use_pct=False) * RW
        ).rename("m_ISMServices")

    # CLI Diffusion — world breadth
    try:
        from ix.core.indicators.growth import oecd_cli_diffusion_world

        _cli_diff = oecd_cli_diffusion_world(lead_months=0, freq="W-FRI")
        if not _cli_diff.empty:
            _cli_diff_m = _cli_diff.resample("ME").last().shift(1)
            rows["g_CLIDiffusion"] = (
                zscore_ism(_cli_diff_m, z_window) * LW
                + zscore_roc(_cli_diff_m, z_window, use_pct=False) * RW
            ).rename("g_CLIDiffusion")
    except Exception as exc:
        log.warning("CLI Diffusion load failed: %s", exc)

    # [DROPPED: g_Permits — post IC -0.023 (DYING). Full IC only +0.026.
    #  Building permits are now covered by the dedicated HousingRegime.]

    # [DROPPED: g_CFNAI — individual IC passes (full +0.087, pre +0.147,
    #  post +0.013) but COMPOSITE IC worsens when added (full -0.007,
    #  post -0.049). Likely correlated with CLIDiffusion, diluting the
    #  stronger signal without adding information.]

    return rows


def load_inflation_indicators(z_window: int) -> dict[str, pd.Series]:
    """Load the ``i_*`` inflation indicator set.

    All inflation indicators use STRUCTURAL ANCHORS instead of rolling mean:
      - ISM Prices Paid: anchored at 50 (expansion/contraction threshold)
      - 5Y Breakeven:   anchored at 2.5%
      - PCE Core YoY:   anchored at 2.5%
      - Wages YoY:      anchored at 3.5%
      - WTI/BCOM YoY:   anchored at 0%
    This eliminates the rolling-mean drift problem (where 3% CPI reads as
    "below average" because the 2021-22 spike inflated the rolling mean).

    Dropped (negative IC@1M vs CL1 target): CPI 3M Ann., Median CPI YoY.
    """
    rows: dict[str, pd.Series] = {}

    # [DROPPED: i_ISMPricesPaid — post IC -0.026 (DYING). Full IC +0.039
    #  but sign-flipped post-2010 against CL1 6M target. ISM prices paid
    #  is manufacturing-focused and has lost predictive power for oil.]

    # 5Y Breakeven inflation expectations — anchored at 2.5%
    be = load_series("T5YIE:PX_LAST")
    if not be.empty:
        rows["i_Breakeven"] = (
            zscore_anchored(be, INFLATION_ANCHOR, z_window) * LW
            + zscore_roc(be, z_window, use_pct=False) * RW
        ).rename("i_Breakeven")

    # [DROPPED: i_PCECore — pre IC -0.040, full IC +0.007 (NOISE).
    #  PCE Core YoY is too lagging for commodity (CL1) forward returns.
    #  The Fed-preferred measure matters for rates, not oil.]

    # [DROPPED: i_Wages — pre IC -0.038, full IC +0.029. Wages YoY is
    #  a lagging indicator with poor pre-2010 signal for commodity forwards.
    #  Wage-price spiral dynamics operate on 12-24M horizon, too slow for
    #  the 6M CL1 target.]

    # [DROPPED: i_WTI — post IC -0.036 (DYING). Full IC only +0.021.
    #  WTI YoY is circular with the CL1 target (oil predicting oil).
    #  The broader i_Commodities (BCOM) captures energy without
    #  the circularity problem.]

    # Bloomberg Commodity Index YoY — broad commodity basket (energy, metals, ags).
    # Captures broader inflation pressure than oil alone. Anchored at 0%.
    bcom = load_series("BCOM-CME:PX_LAST", lag=0)
    if not bcom.empty:
        bcom_yoy = bcom.pct_change(12, fill_method=None) * 100
        rows["i_Commodities"] = (
            zscore_anchored(bcom_yoy, COMMODITY_ANCHOR, z_window) * LW
            + zscore_roc(bcom_yoy, z_window, use_pct=False) * RW
        ).rename("i_Commodities")

    return rows
