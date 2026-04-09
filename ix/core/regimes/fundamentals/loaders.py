"""Shared growth / inflation indicator loaders.

Extracted from the old 2D ``MacroRegime`` so that :class:`GrowthRegime` and
:class:`InflationRegime` can share the same indicator definitions without
carrying the deprecated 2-axis wrapper class.

Both loaders return ``{prefixed_name: z-scored series}`` dicts keyed with
``g_*`` (growth) and ``i_*`` (inflation) prefixes. Indicators use a
25% level z-score + 75% ROC z-score blend. Inflation indicators use
structural anchors (2.5% CPI, 3.5% wages, 0% commodities) instead of
rolling means so cycle regime reads are stable through disinflation eras.

Indicators
----------
Growth (9, one ``m_*`` monitor-only)
    g_InitialClaims · g_ISMNewOrders · g_OECDCLI · g_LEI
    g_Payrolls · g_CLIDiffusion · g_Permits · g_ISM_NO_Inv
    m_ISMServices (monitor-only)
    g_Claims4WMA (loaded but excluded from composite)

Inflation (8)
    i_ISMPricesPaid (anchor 50) · i_CPI3MAnn (anchor 2.5%)
    i_Breakeven (anchor 2.5%)   · i_PCECore (anchor 2.5%)
    i_MedianCPI (anchor 2.5%)   · i_Wages (anchor 3.5%)
    i_WTI (anchor 0%)           · i_Commodities (anchor 0%)
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

    ic_weekly_raw = DbSeries("ICSA")
    ic = (
        ic_weekly_raw.resample("ME").last()
        if not ic_weekly_raw.empty
        else pd.Series(dtype=float)
    )
    if not ic.empty:
        ic_inv = -ic
        rows["g_InitialClaims"] = (
            zscore(ic_inv, z_window) * LW
            + zscore_roc(ic_inv, z_window, use_pct=False) * RW
        ).rename("g_InitialClaims")

        # Claims 4WMA nowcast — monitor-only, excluded from composite
        try:
            ic_4wma = -ic_weekly_raw.rolling(4, min_periods=2).mean()
            ic_4wma_m = ic_4wma.resample("ME").last()
            rows["g_Claims4WMA"] = zscore(ic_4wma_m, z_window).rename(
                "g_Claims4WMA"
            )
        except Exception as exc:
            log.warning("Claims 4WMA nowcast failed: %s", exc)

    ism_no = load_series("ISMNOR_M:PX_LAST", lag=1)
    if not ism_no.empty:
        ism_no_3ma = ism_no.rolling(3, min_periods=1).mean()
        rows["g_ISMNewOrders"] = (
            zscore_ism(ism_no_3ma, z_window) * LW
            + zscore_roc(ism_no_3ma, z_window, use_pct=False) * RW
        ).rename("g_ISMNewOrders")

    oecd = load_series("USA.LOLITOAA.STSA", lag=1)
    if not oecd.empty:
        rows["g_OECDCLI"] = (
            zscore(oecd, z_window) * LW
            + zscore_roc(oecd, z_window, use_pct=True) * RW
        ).rename("g_OECDCLI")

    lei = load_series("USSLIND", lag=1)
    if not lei.empty:
        rows["g_LEI"] = (
            zscore(lei, z_window) * LW
            + zscore_roc(lei, z_window, use_pct=True) * RW
        ).rename("g_LEI")

    nfp = load_series("PAYEMS", lag=1)
    if not nfp.empty:
        nfp_yoy = nfp.pct_change(12, fill_method=None) * 100
        rows["g_Payrolls"] = (
            zscore(nfp_yoy, z_window) * LW
            + zscore_roc(nfp_yoy, z_window, use_pct=False) * RW
        ).rename("g_Payrolls")

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

    # Building Permits
    permit = load_series("PERMIT", lag=1)
    if not permit.empty:
        rows["g_Permits"] = (
            zscore(permit, z_window) * LW
            + zscore_roc(permit, z_window, use_pct=True) * RW
        ).rename("g_Permits")

    # ISM New Orders − Inventories spread
    ism_inv = load_series("ISMINV_M:PX_LAST", lag=1)
    if not ism_no.empty and not ism_inv.empty:
        no_inv = ism_no.reindex(ism_inv.index, method="ffill") - ism_inv
        no_inv_3ma = no_inv.rolling(3, min_periods=1).mean()
        rows["g_ISM_NO_Inv"] = (
            zscore(no_inv_3ma, z_window) * LW
            + zscore_roc(no_inv_3ma, z_window, use_pct=False) * RW
        ).rename("g_ISM_NO_Inv")

    return rows


def load_inflation_indicators(z_window: int) -> dict[str, pd.Series]:
    """Load the ``i_*`` inflation indicator set.

    All inflation indicators use STRUCTURAL ANCHORS instead of rolling mean:
      - ISM Prices Paid: anchored at 50 (expansion/contraction threshold)
      - CPI 3M Ann.:    anchored at 2.5% (Fed target + buffer)
      - 5Y Breakeven:   anchored at 2.5%
      - PCE Core YoY:   anchored at 2.5%
      - Median CPI YoY: anchored at 2.5%
      - Wages YoY:      anchored at 3.5%
      - WTI/BCOM YoY:   anchored at 0%
    This eliminates the rolling-mean drift problem (where 3% CPI reads as
    "below average" because the 2021-22 spike inflated the rolling mean).
    """
    rows: dict[str, pd.Series] = {}

    # ISM Prices Paid — anchored at 50
    ism_pr = load_series("ISMPRI_M:PX_LAST", lag=1)
    if not ism_pr.empty:
        rows["i_ISMPricesPaid"] = (
            zscore_ism(ism_pr, z_window) * LW
            + zscore_roc(ism_pr, z_window, use_pct=False) * RW
        ).rename("i_ISMPricesPaid")

    # CPI — anchored at 2.5%
    cpi_raw = load_series("USPR1980783:PX_LAST", lag=1)
    if not cpi_raw.empty:
        cpi_3m = cpi_raw.pct_change(3, fill_method=None).mul(400)
        cpi_yoy = cpi_raw.pct_change(12, fill_method=None).mul(100)
        rows["i_CPI3MAnn"] = (
            zscore_anchored(cpi_3m, INFLATION_ANCHOR, z_window) * LW
            + zscore_anchored(cpi_yoy, INFLATION_ANCHOR, z_window) * RW
        ).rename("i_CPI3MAnn")

    # 5Y Breakeven inflation expectations — anchored at 2.5%
    be = load_series("T5YIE:PX_LAST")
    if not be.empty:
        rows["i_Breakeven"] = (
            zscore_anchored(be, INFLATION_ANCHOR, z_window) * LW
            + zscore_roc(be, z_window, use_pct=False) * RW
        ).rename("i_Breakeven")

    # PCE Core YoY — Fed's preferred measure, anchored at 2.5%
    pce = load_series("PCEPILFE", lag=1)
    if not pce.empty:
        pce_yoy = pce.pct_change(12, fill_method=None) * 100
        rows["i_PCECore"] = (
            zscore_anchored(pce_yoy, INFLATION_ANCHOR, z_window) * LW
            + zscore_roc(pce_yoy, z_window, use_pct=False) * RW
        ).rename("i_PCECore")

    # Cleveland Fed Median CPI YoY — trimmed-mean measure that removes outliers
    # and captures persistent (non-transitory) inflation. Anchored at 2.5%.
    med_cpi = load_series("MEDCPIM158SFRBCLE", lag=1)
    if not med_cpi.empty:
        # MEDCPIM158SFRBCLE is reported as MoM % change → annualize via rolling 12m sum
        med_cpi_yoy = med_cpi.rolling(12, min_periods=12).sum()
        rows["i_MedianCPI"] = (
            zscore_anchored(med_cpi_yoy, INFLATION_ANCHOR, z_window) * LW
            + zscore_roc(med_cpi_yoy, z_window, use_pct=False) * RW
        ).rename("i_MedianCPI")

    # Average Hourly Earnings YoY — wage-price spiral signal. Anchored at 3.5%
    # (productivity ~1.5% + inflation target ~2% ≈ wage equilibrium).
    wages = load_series("AHETPI", lag=1)
    if not wages.empty:
        wage_yoy = wages.pct_change(12, fill_method=None) * 100
        rows["i_Wages"] = (
            zscore_anchored(wage_yoy, WAGE_ANCHOR, z_window) * LW
            + zscore_roc(wage_yoy, z_window, use_pct=False) * RW
        ).rename("i_Wages")

    # WTI Crude Oil YoY — energy inflation pulse, leading indicator for headline CPI.
    # Anchored at 0% (zero YoY change = no commodity inflation).
    wti = load_series("CL1 Comdty:PX_LAST", lag=0)
    if not wti.empty:
        wti_yoy = wti.pct_change(12, fill_method=None) * 100
        rows["i_WTI"] = (
            zscore_anchored(wti_yoy, COMMODITY_ANCHOR, z_window) * LW
            + zscore_roc(wti_yoy, z_window, use_pct=False) * RW
        ).rename("i_WTI")

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
