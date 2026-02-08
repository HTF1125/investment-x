import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, MonthEndOffset, Cycle
from .style import apply_academic_style, add_zero_line, get_value_label


OECD_CLI_CODES = [
    "USA",
    "TUR",
    "IND",
    "IDN",
    "CHN",
    "KOR",
    "BRA",
    "AUS",
    "CAN",
    "DEU",
    "ESP",
    "FRA",
    "GBR",
    "ITA",
    "JPN",
    "MEX",
]


def OecdCliDiffusion() -> go.Figure:
    """OECD CLI Diffusion Index"""
    try:
        # 1. Fetch CLI for all countries
        series_dict = {
            x: Series(f"{x}.LOLITOAA.STSA:PX_LAST", freq="ME") for x in OECD_CLI_CODES
        }
        cli_data = MultiSeries(**series_dict)

        # 2. Calculate Diffusion
        # a. Calculate MoM difference
        cli_diff = cli_data.diff().dropna(how="all")

        # b. Calculate % positive (Diffusion)
        pos_count = (cli_diff > 0).sum(axis=1)
        valid_count = cli_diff.notna().sum(axis=1)
        diffusion_raw = (pos_count / valid_count).replace(
            [float("inf"), -float("inf")], pd.NA
        ).fillna(0) * 100

        # c. Lead by 3 months (MonthEndOffset)
        # Note: ix.db.query.MonthEndOffset does: shifted = series.index + pd.DateOffset(months=months)
        # This shifts the index forward, meaning current data is projected into the future.
        diffusion = (
            MonthEndOffset(diffusion_raw.to_frame(), 3)
            .iloc[:, 0]
            .resample("W-Fri")
            .ffill()
        )

        # 3. Calculate Cycle on the diffusion index
        diffusion_cycle = Cycle(diffusion.iloc[-52 * 5 :])

        # 4. Fetch ACWI YoY for comparison
        acwi_yoy = (
            Series("ACWI US EQUITY:PX_LAST", freq="W-Fri")
            .ffill()
            .pct_change(52)
            .mul(100)
            .dropna()
        )

        # 5. Combine everything
        df = (
            MultiSeries(
                **{
                    "OECD CLI Diffusion Index (3M Lead)": diffusion,
                    "Cycle": diffusion_cycle,
                    "ACWI YoY (%)": acwi_yoy,
                }
            )
            .dropna(how="all")
            .iloc[-12 * 52 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Diffusion Index (Left)
    col1 = "OECD CLI Diffusion Index (3M Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], "Diffusion (3M Lead)", ".2f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="<b>Diffusion (3M Lead)</b>: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Cycle (Left)
    col2 = "Cycle"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "Cycle", ".2f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="<b>Cycle</b>: %{y:.2f}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 3. ACWI YoY (Right)
    col3 = "ACWI YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col3],
            name=get_value_label(df[col3], "ACWI YoY", ".2f"),
            mode="lines",
            line=dict(width=2),
            hovertemplate="<b>ACWI YoY</b>: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>OECD CLI Diffusion Index</b>"),
        yaxis=dict(
            title="Diffusion Index (%) / Cycle",
            range=[0, 100],  # Diffusion is 0-100%
            tickvals=[0, 20, 40, 50, 60, 80, 100],
        ),
        yaxis2=dict(title="ACWI YoY (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        # Add 50 line for diffusion
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="black",
            opacity=0.3,
            annotation_text="50",
            annotation_position="bottom right",
        )

    return fig
