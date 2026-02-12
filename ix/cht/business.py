import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, StandardScalar, MonthEndOffset, Cycle
from .style import apply_academic_style, add_zero_line, get_value_label


def AsianExportsYoY() -> go.Figure:
    """Asian Exporters YoY Chart (Business)"""
    try:
        df = (
            MultiSeries(
                **{
                    "China": Series("CN.FTEXP").resample("ME").ffill().pct_change(12)
                    * 100,
                    "Taiwan": Series("TW.FTEXP").resample("ME").ffill().pct_change(12)
                    * 100,
                    "Korea": Series("KR.FTEXP").resample("ME").ffill().pct_change(12)
                    * 100,
                    "Singapore": Series("SGFT1039935")
                    .resample("ME")
                    .ffill()
                    .pct_change(12)
                    * 100,
                }
            )
            .rolling(3)
            .mean()
            .iloc[-12 * 10 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                mode="lines",
                line=dict(width=2.5),
                hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Asia Exporters YoY (USD, %, 3MMA)</b>"),
        yaxis_title="YoY Growth (%)",
    )
    fig.update_yaxes(hoverformat=".2f")

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def Mag7CapexGrowth() -> go.Figure:
    """Mag 7 Capex Growth Chart (Business)"""
    try:
        tickers = ["TSLA", "AAPL", "AMZN", "MSFT", "GOOG", "META", "NVDA"]
        freq = "W-Fri"
        # Fetch NTMA (Forward) and LTMA (Backward) series
        ntma_agg = (
            MultiSeries(**{t: Series(f"{t}:FE_CAPEX_NTMA", freq=freq) for t in tickers})
            .dropna()
            .sum(axis=1)
        )
        ltma_agg = (
            MultiSeries(**{t: Series(f"{t}:FE_CAPEX_LTMA", freq=freq) for t in tickers})
            .dropna()
            .sum(axis=1)
        )
        # Calculate growth and smooth
        growth = ntma_agg.div(ltma_agg).sub(1).mul(100).rolling(13).mean()
        df = MultiSeries(**{"Mag 7 Capex NTMA YoY MA13W (%)": growth}).iloc[-52 * 30 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])
    col = "Mag 7 Capex NTMA YoY MA13W (%)"

    for idx, col_name in enumerate(df.columns):
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col_name],
                name=get_value_label(df[col_name], "MAG7 CAPEX Growth", ".2f"),
                mode="lines",
                line=dict(width=3),
                hovertemplate="MAG7 CAPEX Growth: %{y:.2f}%<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>MAG7 CAPEX Growth Expectations</b>"),
        yaxis_title="Expected Growth (%)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def IndustrialProductionLeadingIndicator() -> go.Figure:
    """Industrial Production vs LEI (Business)"""
    try:
        df = MultiSeries(
            **{
                "Industrial Production YoY": StandardScalar(
                    Series("INDPRO:PX_LAST").pct_change(12).mul(100), 36
                ),
                "Leading Indicator 6M Change (Lead 6M)": StandardScalar(
                    MonthEndOffset(
                        Series("US.LEI:PX_LAST").pct_change(6).mul(100), months=6
                    ),
                    36,
                ),
            }
        ).iloc[-12 * 10 - 6 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                mode="lines",
                line=dict(width=2.5),
                hovertemplate=f"{col}: %{{y:.2f}}<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Industrial Production vs Leading Indicator</b>"),
        yaxis_title="Standardized Value (Z-Score)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def HeavyTruckSalesUnemployment() -> go.Figure:
    """Heavy Truck Sales vs Unemployment Rate (Reversed Scale)"""
    try:
        df = MultiSeries(
            **{
                "Heavy Truck Sales (12m Sum)": Series("BEADETTEMH3@US:PX_LAST")
                .rolling(12)
                .sum(),
                "Unemployment Rate (%)": Series("BLSLNS14000001:PX_LAST"),
            }
        ).iloc[-12 * 30 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Heavy Truck Sales (Left Axis - Reversed)
    col1 = "Heavy Truck Sales (12m Sum)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"{col1}: %{{y:,.2f}}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # Unemployment Rate (Right Axis)
    col2 = "Unemployment Rate (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".2f"),
            mode="lines",
            line=dict(width=2.5, dash="dot"),
            hovertemplate=f"{col2}: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Heavy Truck Sales vs. Unemployment Rate</b>"),
    )

    # Reverse the primary y-axis for truck sales
    fig.update_yaxes(
        title="Truck Sales (Units) - Reversed",
        secondary_y=False,
        autorange="reversed",
    )
    fig.update_yaxes(
        title="Unemployment Rate (%)",
        secondary_y=True,
        showgrid=False,
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])

    return fig


def EmpireStateManufacturing() -> go.Figure:
    """Empire State Manufacturing Survey (Current, Next 6M, Spread)"""
    try:
        df = MultiSeries(
            **{
                "Current": Series("USSU0009518:PX_LAST").rolling(3).mean(),
                "Next 6M": Series("USSU0009558:PX_LAST").rolling(3).mean(),
                "Spread": (
                    Series("USSU0009558:PX_LAST") - Series("USSU0009518:PX_LAST")
                )
                .rolling(3)
                .mean(),
            }
        ).iloc[-12 * 20 :]
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
                line=dict(width=2.5),
                hovertemplate=f"{col}: %{{y:.2f}}<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Empire State Manufacturing Survey</b>"),
        yaxis_title="Diffusion Index",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def SemiconductorBillingsYoY() -> go.Figure:
    """Semiconductor Billings YoY & Contribution to Growth (Business)"""
    try:
        # 1. Fetch levels for all regions
        regions = {
            "America": Series("WDIN8158464:PX_LAST", freq="ME"),
            "Europe": Series("WDIN8158465:PX_LAST", freq="ME"),
            "Japan": Series("WDIN8158466:PX_LAST", freq="ME"),
            "Apac": Series("WDIN8158467:PX_LAST", freq="ME"),
        }
        levels = MultiSeries(**regions).dropna(how="all").ffill()

        # 2. Calculate World level and lag
        world_level = levels.sum(axis=1)
        world_lag_12 = world_level.shift(12)

        # 3. Calculate Contributions to Growth (%)
        # Formula: (Region_t - Region_t-12) / World_Total_t-12 * 100
        contributions = levels.diff(12).div(world_lag_12, axis=0).mul(100)

        # 4. Calculate World YoY (%)
        world_yoy = world_level.pct_change(12).mul(100)

        # Combine for plotting
        df = pd.concat([contributions, world_yoy.rename("World YoY")], axis=1)
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Plot Regional Contributions as Bars
    colors = {
        "America": "#3b82f6",  # Blue
        "Europe": "#8b5cf6",  # Purple
        "Japan": "#ec4899",  # Pink
        "Apac": "#10b981",  # Emerald
    }
    for col in ["America", "Europe", "Japan", "Apac"]:
        if col in df.columns:
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[col],
                    name=col,
                    marker=dict(color=colors.get(col)),
                    hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
                )
            )

    # Plot World YoY as a Line
    if "World YoY" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["World YoY"],
                name=get_value_label(df["World YoY"], "World YoY", ".2f"),
                mode="lines",
                line=dict(width=3, color="#f8fafc"),
                hovertemplate="World YoY: %{y:.2f}%<extra></extra>",
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(
            text="<b>Semiconductor Billings YoY & Contribution to Growth (%)</b>"
        ),
        yaxis_title="Growth / Contribution (%)",
        barmode="stack",
    )

    if not df.empty:
        # Default view to last 5 years, but all data is available
        start_date = df.index[-1] - pd.DateOffset(years=10)
        fig.update_xaxes(range=[start_date, df.index[-1]])
        add_zero_line(fig)

    return fig


def SemiconductorBillings() -> go.Figure:
    """Semiconductor Billings (Billions) Chart (Business)"""
    try:
        df = (
            MultiSeries(
                **{
                    "America": Series("WDIN8158464:PX_LAST", freq="ME"),
                    "Europe": Series("WDIN8158465:PX_LAST", freq="ME"),
                    "Japan": Series("WDIN8158466:PX_LAST", freq="ME"),
                    "Apac": Series("WDIN8158467:PX_LAST", freq="ME"),
                    "World": Series("WDIN8158468:PX_LAST", freq="ME"),
                }
            )
            .rolling(12)
            .sum()
            .mul(1000)
            .div(1_000_000_000)
            .dropna(how="all")
            .ffill()
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    colors = {
        "America": "#3b82f6",
        "Europe": "#8b5cf6",
        "Japan": "#ec4899",
        "Apac": "#10b981",
        "World": "#f8fafc",
    }
    for col in ["America", "Europe", "Japan", "Apac", "World"]:
        if col not in df.columns:
            continue

        if col == "World":
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    name=get_value_label(df[col], col, ".2f"),
                    mode="lines",
                    line=dict(width=3, color=colors["World"]),
                    hovertemplate=f"{col}: %{{y:.2f}}B<extra></extra>",
                    connectgaps=True,
                )
            )
        else:
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df[col],
                    name=col,
                    marker=dict(color=colors.get(col)),
                    hovertemplate=f"{col}: %{{y:.2f}}B<extra></extra>",
                )
            )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Semiconductor Billings (LTM Sum, USD Billions)</b>"),
        yaxis_title="Billings (USD Billions)",
        barmode="stack",
    )

    if not df.empty:
        # Default view to last 10 years, but all data is available
        start_date = df.index[-1] - pd.DateOffset(years=10)
        fig.update_xaxes(range=[start_date, df.index[-1]])

    return fig
