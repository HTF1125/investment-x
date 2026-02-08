import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, StandardScalar, Offset, Cycle
from .style import apply_academic_style, add_zero_line, get_value_label


def CompositeLeadingIndicator() -> go.Figure:
    """Composite Leading Indicator (Liquidity, Growth, Risk)"""
    try:
        freq = "W-Fri"
        window_std = 156  # 3 years weekly

        # --- 1. LIQUIDITY PILLAR ---
        walcl = Series("WALCL:PX_LAST", freq=freq)
        wtregen = Series("WTREGEN:PX_LAST", freq=freq)
        rrp = Series("RRPONTSYD:PX_LAST", freq=freq).mul(1000)
        net_liq = walcl - wtregen - rrp
        net_liq_comp = StandardScalar(
            net_liq.ffill().pct_change(52).rolling(4).mean().mul(100), window_std
        )
        dxy = Series("DXY INDEX:PX_LAST", freq=freq)
        dxy_comp = StandardScalar(
            dxy.pct_change(52).rolling(4).mean().mul(-100), window_std
        )
        liquidity_pillar = (net_liq_comp + dxy_comp) / 2

        # --- 2. GROWTH PILLAR ---
        itb = Series("ITB US EQUITY:PX_LAST", freq=freq)
        spy = Series("SPY US EQUITY:PX_LAST", freq=freq)
        itb_spy = itb / spy
        itb_spy_comp = StandardScalar(
            itb_spy.pct_change(52).rolling(4).mean().mul(100), window_std
        )
        soxx = Series("SOXX US EQUITY:PX_LAST", freq=freq)
        soxx_spy = soxx / spy
        soxx_spy_comp = StandardScalar(
            soxx_spy.pct_change(52).rolling(4).mean().mul(100), window_std
        )
        hg1 = Series("HG1 COMDTY:PX_LAST", freq=freq)
        gc1 = Series("GC1 COMDTY:PX_LAST", freq=freq)
        cu_au = hg1 / gc1
        cu_au_comp = StandardScalar(
            cu_au.pct_change(52).rolling(4).mean().mul(100), window_std
        )
        growth_pillar = (itb_spy_comp + soxx_spy_comp + cu_au_comp) / 3

        # --- 3. RISK PILLAR ---
        hyg = Series("HYG US EQUITY:PX_LAST", freq=freq)
        ief = Series("IEF US EQUITY:PX_LAST", freq=freq)
        hyg_ief = hyg / ief
        hyg_ief_comp = StandardScalar(
            hyg_ief.pct_change(52).rolling(4).mean().mul(100), window_std
        )
        vix = Series("VIX INDEX:PX_LAST", freq=freq)
        vix_comp = StandardScalar(vix.rolling(13).mean().mul(-1), window_std)
        tlt = Series("TLT US EQUITY:PX_LAST", freq=freq)
        tlt_vol_comp = StandardScalar(tlt.rolling(13).std().mul(-1), window_std)
        risk_pillar = (hyg_ief_comp + vix_comp + tlt_vol_comp) / 3

        # --- COMPOSITE ---
        composite_raw = (liquidity_pillar + growth_pillar + risk_pillar) / 3
        # Offset by 13 weeks (3M Lead)
        composite_lead = Offset(composite_raw, days=7 * 13)
        # Cycle
        cycle = Cycle(composite_lead.iloc[-52 * 10 :])
        # S&P500 YoY
        spx = Series("SPX INDEX:PX_LAST").resample("W-Fri").last()
        spx_yoy = spx.pct_change(52).mul(100)

        df = MultiSeries(
            **{
                "S&P500 YoY (%)": spx_yoy,
                "Composite (3M Lead)": composite_lead,
                "Cycle": cycle,
            }
        ).iloc[-52 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Composite (Lead)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Composite (3M Lead)"],
            name=get_value_label(df["Composite (3M Lead)"], "Composite (3M Lead)"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate="Composite (3M Lead): %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 2. Cycle
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Cycle"],
            name=get_value_label(df["Cycle"], "Cycle"),
            mode="lines",
            line=dict(width=2.0),
            hovertemplate="Cycle: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 3. S&P500 YoY (Secondary Axis)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["S&P500 YoY (%)"],
            name=f"S&P500 YoY ({df['S&P500 YoY (%)'].dropna().iloc[-1]:.2f}%)",
            mode="lines",
            line=dict(width=2),
            hovertemplate="S&P500 YoY: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Composite Leading Indicator</b>"),
        yaxis=dict(title="Composite Index / Cycle"),
        yaxis2=dict(title="S&P500 YoY (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def IsmSwedenPmi() -> go.Figure:
    """ISM and Sweden PMI"""
    try:
        df = MultiSeries(
            **{
                "ISM(US)": Series("ISMPMI@M:PX_LAST"),
                "Sweden": Series("SE.PMIM:PX_LAST"),
            }
        ).iloc[-240:]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".1f"),
                mode="lines",
                line=dict(width=2.5),
                hovertemplate=f"{col}: %{{y:.1f}}<extra></extra>",
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>ISM and Sweden PMI</b>"),
        yaxis_title="PMI Index",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        # Threshold line at 50
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="black",
            annotation_text="50",
            annotation_position="bottom right",
            opacity=0.5,
        )

    return fig


def MarketCompositeViews() -> go.Figure:
    """Market Composite Views"""
    try:
        freq = "W-Fri"
        lead_days = 7 * 13
        # Components of Market Implied Growth
        ratios = MultiSeries(
            **{
                "Homebuild/Market": Offset(
                    Series("ITB US EQUITY:PX_LAST", freq=freq)
                    .div(Series("SPY US EQUITY:PX_LAST", freq=freq))
                    .dropna()
                    .pct_change(52)
                    .mul(100),
                    days=lead_days,
                ),
                "Beta/LowVol": Offset(
                    Series("SPHB US EQUITY:PX_LAST", freq=freq)
                    .div(Series("SPLV US EQUITY:PX_LAST", freq=freq))
                    .dropna()
                    .pct_change(52)
                    .mul(100),
                    days=lead_days,
                ),
                "Tech/Energy": Offset(
                    Series("XLK US EQUITY:PX_LAST", freq=freq)
                    .div(Series("XLE US EQUITY:PX_LAST", freq=freq))
                    .dropna()
                    .pct_change(52)
                    .mul(100),
                    days=lead_days,
                ),
                "Market/Commodity": Offset(
                    Series("SPY US EQUITY:PX_LAST", freq=freq)
                    .div(Series("DBC US EQUITY:PX_LAST", freq=freq))
                    .dropna()
                    .pct_change(52)
                    .mul(100),
                    days=lead_days,
                ),
            }
        )
        market_implied_growth = ratios.mean(axis=1)
        spx_yoy = Series("SPY US EQUITY:PX_LAST", freq=freq).pct_change(52).mul(100)

        df = MultiSeries(
            **{
                "Market Implied Growth (13W Lead)": market_implied_growth,
                "S&P500 YoY (%)": spx_yoy,
            }
        ).iloc[-52 * 10 - 13 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Market Implied Growth (Left Axis)
    col_lead = "Market Implied Growth (13W Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_lead],
            name=get_value_label(df[col_lead], "Implied Growth Index", ".2f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="Implied Growth Index: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 2. S&P 500 YoY (Right Axis)
    col_spx = "S&P500 YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_spx],
            name=get_value_label(df[col_spx], "S&P500 YoY", ".2f"),
            mode="lines",
            line=dict(width=2),
            hovertemplate="S&P500 YoY: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Market Composite Views</b>"),
        yaxis=dict(title="Implied Growth Index"),
        yaxis2=dict(title="S&P500 YoY (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def CompositeLeadingIndicators() -> go.Figure:
    """Composite Leading Indicators (LEI, ISM, etc)"""
    try:
        df = MultiSeries(
            **{
                "US LEI": Series("US.LEI:PX_LAST").ffill().pct_change(12).mul(100),
                "ISM(US)": Series("ISMPMI@M:PX_LAST").ffill().sub(50),
                "Business Formation": Series("USSU7809213:PX_LAST")
                .resample("ME")
                .ffill()
                .rolling(6)
                .mean()
                .pct_change(12)
                .mul(100),
                "S&P 500 Momentum (6MMA)": Series("SPX INDEX:PX_LAST", freq="ME")
                .ffill()
                .rolling(6)
                .mean()
                .pct_change(12)
                .mul(100),
            }
        ).iloc[-12 * 20 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for idx, col in enumerate(df.columns):

        # Divide components into dual axes
        is_secondary = col in ["Business Formation", "S&P 500 Momentum (6MMA)"]

        fmt = ".1f" if col == "ISM(US)" else ".2f"

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, fmt),
                mode="lines",
                line=dict(width=2.5),
                hovertemplate=f"{col}: %{{y:{fmt}}}<extra></extra>",
                connectgaps=True,
            ),
            secondary_y=is_secondary,
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Composite Leading Indicators</b>"),
        yaxis=dict(title="LEI YoY (%) / ISM (pts)"),
        yaxis2=dict(title="Business Formation / SPX Momentum (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def _get_market_implied_components() -> pd.DataFrame:
    """Helper to build market implied business cycle components."""
    components = (
        MultiSeries(
            **{
                "Tech/Utils": (
                    Series("XLI US EQUITY:PX_LAST") / Series("XLU US EQUITY:PX_LAST")
                ),
                "HighBeta/LowVol": (
                    Series("SPHB US EQUITY:PX_LAST") / Series("SPLV US EQUITY:PX_LAST")
                ),
                "Small/Large": (
                    Series("IJR US EQUITY:PX_LAST") / Series("SPY US EQUITY:PX_LAST")
                ),
                "AUD/JPY": (
                    Series("USDJPY CURNCY:PX_LAST") / Series("USDAUD CURNCY:PX_LAST")
                ),
                "Semi/Staples": (
                    Series("SMH US EQUITY:PX_LAST") / Series("XLP US EQUITY:PX_LAST")
                ),
            }
        )
        .resample("W-Fri")
        .ffill()
        .pct_change(52)
        .mul(100)
    )
    return components


def MarketImpliedBusinessCycle() -> go.Figure:
    """Market Implied Business Cycle vs S&P500 YoY"""
    try:
        components = _get_market_implied_components()

        df = MultiSeries(
            **{
                "Market Implied Cycle (13W Lead)": Offset(
                    components.mean(axis=1), days=7 * 13
                ),
                "SPX YoY (%)": Series("SPY US EQUITY:PX_LAST")
                .resample("W-Fri")
                .ffill()
                .pct_change(52)
                .mul(100),
            }
        ).iloc[-52 * 10 - 7 * 13 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Market Implied Cycle (Primary Y-Axis)
    col1 = "Market Implied Cycle (13W Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"{col1}: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # SPX YoY (Secondary Y-Axis)
    col2 = "SPX YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"{col2}: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Market Implied Business Cycle</b>"),
    )

    fig.update_yaxes(
        title="Implied Cycle (%)",
        secondary_y=False,
    )
    fig.update_yaxes(
        title="SPX YoY (%)",
        secondary_y=True,
        showgrid=False,
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def MarketImpliedBusinessCycle_Components() -> go.Figure:
    """Market Implied Business Cycle - Component Breakdown"""
    try:
        df = _get_market_implied_components().iloc[-52 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for col in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                mode="lines",
                line=dict(width=2),
                hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Market Implied Cycle Components</b>"),
        yaxis_title="YoY Change (%)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
