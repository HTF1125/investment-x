import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import timedelta
from ix.db.query import Series, MultiSeries, Offset, Rebase
from .style import apply_academic_style, add_zero_line, get_value_label


def GoldBullMarkets() -> go.Figure:
    """Gold Bull Market Performances"""
    try:
        df = MultiSeries(
            **{
                "Gold (1971.08-1979.12)": Offset(
                    Rebase(
                        Series("GOLD CURNCY:PX_LAST")
                        .resample("W-Fri")
                        .last()
                        .loc["1971-08":"1979-12"]
                    ),
                    days=7 * 52 * 50 - 65 * 7,
                ),
                "Gold (2001.02-2011.08)": Offset(
                    Rebase(
                        Series("GOLD CURNCY:PX_LAST")
                        .resample("W-Fri")
                        .last()
                        .loc["2001-02":"2011-08"]
                    ),
                    days=7 * 52 * 20 - 44 * 7,
                ),
                "Gold (2020.03-Present)": Rebase(
                    Series("GOLD CURNCY:PX_LAST")
                    .resample("W-Fri")
                    .last()
                    .loc["2020-03":]
                ),
            }
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Define styles mapping based on col names used in build_data
    styles = {
        "Gold (1971.08-1979.12)": {
            "dash": "solid",
            "width": 2,
            "name": "1971.08 ~ 1979.12",
        },
        "Gold (2001.02-2011.08)": {
            "dash": "solid",
            "width": 2,
            "name": "2001.02 ~ 2011.08",
        },
        "Gold (2020.03-Present)": {
            "dash": "solid",
            "width": 4,
            "name": "2020.03 ~ Present",
        },
    }

    for col in df.columns:
        if col in styles:
            style = styles[col]
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    name=get_value_label(df[col], style["name"], ".1f"),
                    mode="lines",
                    line=dict(
                        width=style["width"],
                        dash=style["dash"],
                    ),
                    hovertemplate=f"{styles[col]['name']}: %{{y:.2f}}<extra></extra>",
                    connectgaps=True,
                )
            )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Gold Bull Market Performances</b>"),
        yaxis=dict(title="Performance (Rebased=1.0)", type="log", tickformat=".1f"),
    )

    # Custom X Range logic from original
    start_date = pd.to_datetime("2020-01-01")
    view_end_date = start_date + timedelta(days=365 * 12)
    fig.update_xaxes(range=[start_date, view_end_date], tickformat="%Y.%m")

    # Rebase baseline (1.00)
    fig.add_hline(y=1, line_color="black", opacity=0.3)

    return fig
