import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, StandardScalar, Cycle
from .style import apply_academic_style, add_zero_line, get_value_label


def FinancialConditions() -> go.Figure:
    """Financial Conditions (Proprietary) Chart"""
    try:
        # 1. Calculate Component FCIs
        fci_rates_credit = (
            MultiSeries(
                **{
                    "Treasury10Y": StandardScalar(
                        -Series("TRYUS10Y:PX_YTM", freq="W-Fri").ffill(), 156
                    ),
                    "Mortgage": StandardScalar(
                        -Series("MORTGAGE30US", freq="W-Fri").ffill(), 156
                    ),
                    "HY Spread": StandardScalar(
                        -Series("BAMLH0A0HYM2:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                }
            )
            .ffill()
            .infer_objects(copy=False)
            .mean(axis=1)
        )

        fci_equities = (
            MultiSeries(
                **{
                    "S&P500": StandardScalar(
                        Series("SPX Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Nasdaq": StandardScalar(
                        Series("CCMP Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Small/Large": StandardScalar(
                        Series("RTY INDEX:PX_LAST", freq="W-Fri").ffill()
                        / Series("SPX INDEX:PX_LAST", freq="W-Fri").ffill(),
                        156,
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )

        fci_fx_commodity = (
            MultiSeries(
                **{
                    "Dollar": StandardScalar(
                        -Series("DXY Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "WTI": StandardScalar(
                        -Series("WTI Comdty:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )

        fci_risk = StandardScalar(
            -Series("VIX INDEX:PX_LAST", freq="W-Fri").ffill(), 156
        )

        # 2. Main FCI
        fci_proprietary = (
            MultiSeries(
                **{
                    "FCI - Rates/Credit": fci_rates_credit,
                    "FCI - Equities": fci_equities,
                    "FCI - FX & Commodity": fci_fx_commodity,
                    "FCI - Risk (VIX)": fci_risk,
                }
            )
            .mean(axis=1)
            .ewm(span=26)
            .mean()
            .mul(100)
        )

        # 3. Cycle Calculation Base
        fci_equities_cycle = (
            MultiSeries(
                **{
                    "S&P500": StandardScalar(
                        Series("SPX Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Nasdaq": StandardScalar(
                        Series("CCMP Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Small/Large": StandardScalar(
                        Series("RTY INDEX:PX_LAST", freq="W-Fri").ffill()
                        / Series("SPX INDEX:PX_LAST", freq="W-Fri").ffill(),
                        156,
                    ),
                    "Cyclical/Defensive": StandardScalar(
                        Series("XLY INDEX:PX_LAST", freq="W-Fri").ffill()
                        / Series("XLP INDEX:PX_LAST", freq="W-Fri").ffill(),
                        156,
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )

        fci_cycle_base = (
            MultiSeries(
                **{
                    "FCI - Rates/Credit": fci_rates_credit,
                    "FCI - Equities": fci_equities_cycle,
                    "FCI - FX & Commodity": fci_fx_commodity,
                    "FCI - Risk (VIX)": fci_risk,
                }
            )
            .mean(axis=1)
            .ewm(span=26)
            .mean()
            .mul(100)
        )

        # 4. Final Series
        fci_cycle = Cycle(fci_cycle_base.dropna().iloc[-52 * 5 :])
        fci_fed_scaled = Series("USSU8083177:PX_LAST", freq="W-Fri").ffill().mul(-50)
        spx_yoy = Series("SPX INDEX:PX_LAST", freq="W-Fri").pct_change(52).mul(100)

        df = (
            MultiSeries(
                **{
                    "FCI (Proprietary)": fci_proprietary,
                    "Cycle": fci_cycle,
                    "FCI (Fed Model Scaled)": fci_fed_scaled,
                    "S&P500 YoY (%)": spx_yoy,
                }
            )
            .dropna(how="all")
            .iloc[-52 * 10 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. FCI (Proprietary)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["FCI (Proprietary)"],
            name=get_value_label(df["FCI (Proprietary)"], "FCI (Proprietary)", ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate="<b>FCI (Proprietary)</b>: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 2. Cycle
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Cycle"],
            name=get_value_label(df["Cycle"], "Cycle", ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate="<b>Cycle</b>: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 3. FCI (Fed Model Scaled)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["FCI (Fed Model Scaled)"],
            name=get_value_label(
                df["FCI (Fed Model Scaled)"], "FCI (Fed Model)", ".2f"
            ),
            mode="lines",
            line=dict(width=2.0),
            hovertemplate="<b>FCI (Fed Model)</b>: %{y:.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 4. S&P500 YoY - Sec Axis
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["S&P500 YoY (%)"],
            name=get_value_label(df["S&P500 YoY (%)"], "S&P500 YoY", "+.2f"),
            mode="lines",
            line=dict(width=2.0),
            hovertemplate="<b>S&P500 YoY</b>: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Financial Conditions (Proprietary)</b>"),
        yaxis=dict(title="Index / Cycle"),
        yaxis2=dict(title="YoY (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def FinancialConditionsComponents() -> go.Figure:
    """FCI Components breakdown chart"""
    try:
        # Re-calc components (simplified for brevity, often better to share calculation code but copying for standalone func)
        # Rates/Credit
        fci_rates_credit = (
            MultiSeries(
                **{
                    "Treasury10Y": StandardScalar(
                        -Series("TRYUS10Y:PX_YTM", freq="W-Fri").ffill(), 156
                    ),
                    "Mortgage": StandardScalar(
                        -Series("MORTGAGE30US", freq="W-Fri").ffill(), 156
                    ),
                    "HY Spread": StandardScalar(
                        -Series("BAMLH0A0HYM2:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )
        # Equities
        fci_equities = (
            MultiSeries(
                **{
                    "S&P500": StandardScalar(
                        Series("SPX Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Nasdaq": StandardScalar(
                        Series("CCMP Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "Small/Large": StandardScalar(
                        Series("RTY INDEX:PX_LAST", freq="W-Fri").ffill()
                        / Series("SPX INDEX:PX_LAST", freq="W-Fri").ffill(),
                        156,
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )
        # FX/Commodities
        fci_fx_commodity = (
            MultiSeries(
                **{
                    "Dollar": StandardScalar(
                        -Series("DXY Index:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                    "WTI": StandardScalar(
                        -Series("WTI Comdty:PX_LAST", freq="W-Fri").ffill(), 156
                    ),
                }
            )
            .astype(float)
            .ffill()
            .mean(axis=1)
        )
        # Risk
        fci_risk = StandardScalar(
            -Series("VIX INDEX:PX_LAST", freq="W-Fri").ffill(), 156
        )

        df = (
            MultiSeries(
                **{
                    "Rates/Credit": fci_rates_credit.ewm(span=26).mean().mul(100),
                    "Equities": fci_equities.ewm(span=26).mean().mul(100),
                    "FX/Commodities": fci_fx_commodity.ewm(span=26).mean().mul(100),
                    "Risk": fci_risk.ewm(span=26).mean().mul(100),
                }
            )
            .dropna(how="all")
            .iloc[-52 * 10 :]
        )
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
                line=dict(
                    width=2.0,
                ),
                hovertemplate=f"<b>{col}</b>: %{{y:.2f}}<extra></extra>",
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>FCI Components</b>"),
        yaxis_title="Index Contribution (Scaled)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
