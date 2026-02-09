import plotly.graph_objects as go


from plotly.subplots import make_subplots


import pandas as pd


from ix.db.query import Series, MultiSeries


from .style import apply_academic_style, add_zero_line, get_value_label


def GlobalLiquidity() -> go.Figure:
    """Global Liquidity (Assets & M2)"""

    try:

        # 1. Global Central Bank Assets

        cb_assets = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .sum(axis=1)
            .div(10**12)
            .resample("W-Fri")
            .last()
        )

        # 2. Global Money Supply (M2)

        m2_supply = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .sum(axis=1)
            .div(10**12)
            .resample("W-Fri")
            .last()
        )

        df = MultiSeries(
            **{
                "Global Central Bank Asset ($Tr)": cb_assets,
                "Global Money Supply ($Tr)": m2_supply,
            }
        ).iloc[-52 * 10 :]

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Assets (Left)

    col1 = "Global Central Bank Asset ($Tr)"

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], "CB Assets ($Tr)", ".2f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="CB Assets ($Tr): %{y:.2f}T<extra></extra>",
        ),
        secondary_y=False,
    )

    # 2. M2 (Right)

    col2 = "Global Money Supply ($Tr)"

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "Money Supply ($Tr)", ".2f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="Money Supply ($Tr): %{y:.2f}T<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Global Liquidity (Assets & M2)</b>"),
        yaxis=dict(title="CB Assets ($Tr)"),
        yaxis2=dict(title="Money Supply ($Tr)", showgrid=False),
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig


def GlobalLiquidityYoY() -> go.Figure:
    """Global Liquidity YoY Growth"""

    try:

        # 1. Assets YoY

        cb_assets_yoy = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .sum(axis=1)
            .div(10**12)
            .resample("W-Fri")
            .last()
            .pct_change(52)
            .mul(100)
        )

        # 2. M2 YoY

        m2_supply_yoy = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .sum(axis=1)
            .div(10**12)
            .resample("W-Fri")
            .last()
            .pct_change(52)
            .mul(100)
        )

        df = MultiSeries(
            **{
                "Global Central Bank Asset YoY ($, %)": cb_assets_yoy,
                "Global Money Supply YoY($, %)": m2_supply_yoy,
            }
        ).iloc[-52 * 10 :]

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # 1. Assets YoY

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Global Central Bank Asset YoY ($, %)"],
            name=get_value_label(
                df["Global Central Bank Asset YoY ($, %)"], "CB Assets YoY", "+.2f"
            ),
            mode="lines",
            line=dict(width=3),
            hovertemplate="CB Assets YoY: %{y:.2f}%<extra></extra>",
        )
    )

    # 2. M2 YoY

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Global Money Supply YoY($, %)"],
            name=get_value_label(
                df["Global Money Supply YoY($, %)"], "Money Supply YoY", "+.2f"
            ),
            mode="lines",
            line=dict(width=3),
            hovertemplate="Money Supply YoY: %{y:.2f}%<extra></extra>",
        )
    )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Global Liquidity YoY Growth</b>"),
        yaxis=dict(title="YoY Growth (%)"),
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

        add_zero_line(fig)

    return fig


def _contribution_to_growth(df: pd.DataFrame, period: int = 52) -> pd.DataFrame:
    """Helper for contribution calculation"""

    total = df.sum(axis=1)

    prev_total = total.shift(period)
    diff = df.diff(period)

    contributions = diff.div(prev_total, axis=0).mul(100)

    return contributions


def GlobalAssetContribution() -> go.Figure:
    """Global Central Bank Asset YoY - Contribution"""

    try:

        raw_assets = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.CBASSET:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .resample("W-Fri")
            .last()
            .ffill()
        )

        df = _contribution_to_growth(raw_assets, period=52).iloc[-52 * 1 :]

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    countries = ["US", "EU", "JP", "CN", "KR", "GB"]

    # We use COLORWAY to color these, assigning one color per country

    # Hardcoding color map for consistency

    for country in countries:

        if country in df.columns:

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[country],
                    name=get_value_label(df[country], country, "+.2f"),
                    hovertemplate=f"{country}: %{{y:.2f}}%<extra></extra>",
                )
            )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Global Central Bank Asset YoY - Contribution</b>"),
        yaxis=dict(title="Contribution to Growth (pp)"),
        barmode="relative",
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

        add_zero_line(fig)

    return fig


def GlobalMoneySupplyContribution() -> go.Figure:
    """Global Money Supply YoY - Contribution"""

    try:

        raw_m2 = (
            MultiSeries(
                **{
                    "US": Series(
                        "US.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "EU": Series(
                        "EUZ.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "JP": Series(
                        "JP.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "CN": Series(
                        "CN.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "KR": Series(
                        "KR.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                    "GB": Series(
                        "GB.MAM2:PX_LAST", scale=1, ccy="USD", freq="D"
                    ).ffill(),
                }
            )
            .ffill()
            .resample("W-Fri")
            .last()
            .ffill()
        )

        df = _contribution_to_growth(raw_m2, period=52).iloc[-52 * 1 :]

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    countries = ["US", "EU", "JP", "CN", "KR", "GB"]

    for country in countries:

        if country in df.columns:

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[country],
                    name=get_value_label(df[country], country, "+.2f"),
                    hovertemplate=f"{country}: %{{y:.2f}}%<extra></extra>",
                )
            )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Global Money Supply YoY - Contribution</b>"),
        yaxis=dict(title="Contribution to Growth (pp)"),
        barmode="relative",
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

        add_zero_line(fig)

    return fig


def FedNetLiquidity() -> go.Figure:
    """Fed Liquidity"""

    try:
        df = (
            MultiSeries(
                **{
                    "Total Asset": Series("WALCL:PX_LAST", freq="W-Fri").ffill(),
                    "Treasury General Account": -Series(
                        "WTREGEN:PX_LAST", freq="W-Fri"
                    ).ffill(),
                    "Reverse Repo": -Series("RRPONTSYD:PX_LAST", freq="W-Fri")
                    .ffill()
                    .mul(1000),
                }
            )
            .div(10**3)
            .iloc[-52 * 5 :]
        )

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    components = ["Total Asset", "Treasury General Account", "Reverse Repo"]

    for col in components:

        if col in df.columns:

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[col],
                    name=get_value_label(df[col], col, "+.2f"),
                    hovertemplate=f"{col}: %{{y:.2f}}B<extra></extra>",
                )
            )

    # Net Impulse Line

    net_impulse = df.sum(axis=1)

    fig.add_trace(
        go.Scatter(
            x=net_impulse.index,
            y=net_impulse,
            name=get_value_label(net_impulse, "Net Liquidity", "+.2f"),
            mode="lines",
            line=dict(width=3),
            opacity=0.8,
            hovertemplate="Net Liquidity: %{y:.2f}B<extra></extra>",
        )
    )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Fed Net Liquidity</b>"),
        yaxis=dict(title="Liquidity (Billions USD)"),
        barmode="relative",
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig


def FedNetLiquidityImpulse() -> go.Figure:
    """Fed Liquidity Impulse"""

    try:
        df = (
            MultiSeries(
                **{
                    "Total Asset": Series("WALCL:PX_LAST", freq="W-Fri").ffill(),
                    "Treasury General Account": -Series(
                        "WTREGEN:PX_LAST", freq="W-Fri"
                    ).ffill(),
                    "Reverse Repo": -Series("RRPONTSYD:PX_LAST", freq="W-Fri")
                    .ffill()
                    .mul(1000),
                }
            )
            .div(10**3)
            .diff(52)
            .iloc[-52 * 5 :]
        )

    except Exception as e:

        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    components = ["Total Asset", "Treasury General Account", "Reverse Repo"]

    for col in components:

        if col in df.columns:

            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[col],
                    name=get_value_label(df[col], col, "+.2f"),
                    hovertemplate=f"{col}: %{{y:.2f}}B<extra></extra>",
                )
            )

    # Net Impulse Line

    net_impulse = df.sum(axis=1)

    fig.add_trace(
        go.Scatter(
            x=net_impulse.index,
            y=net_impulse,
            name=get_value_label(net_impulse, "Net Liquidity Impulse", "+.2f"),
            mode="lines",
            line=dict(width=3),
            opacity=0.8,
            hovertemplate="Net Liquidity Impulse: %{y:.2f}B<extra></extra>",
        )
    )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text="<b>Fed Liquidity Impulse</b>"),
        yaxis=dict(title="Impulse (Billions USD)"),
        barmode="relative",
    )

    if not df.empty:

        fig.update_xaxes(range=[df.index[0], df.index[-1]])

        add_zero_line(fig)

    return fig
