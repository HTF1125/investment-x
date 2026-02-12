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


def OecdCliDiffusionIndex_Composite() -> go.Figure:
    """OECD CLI Diffusion Index Composite"""
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
        diffusion_cycle = Cycle(diffusion.iloc[-52 * 10 :])

        # 4. Fetch ACWI YoY for comparison
        acwi_yoy = (
            Series("892400:FG_TOTAL_RET_IDX")
            .resample("W-Fri")
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
            line=dict(width=3, color="#f8fafc"),
            hovertemplate="Diffusion (3M Lead): %{y:.2f}%<extra></extra>",
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
            line=dict(width=3, color="#ef4444"),
            hovertemplate="Cycle: %{y:.2f}<extra></extra>",
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
            line=dict(width=2, color="#f59e0b"),
            hovertemplate="ACWI YoY: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>OECD CLI Diffusion Index - Composite</b>"),
        yaxis=dict(
            title="Diffusion Index (%) / Cycle",
            range=[0, 100],  # Diffusion is 0-100%
            tickvals=[0, 20, 40, 50, 60, 80, 100],
        ),
        yaxis2=dict(title="ACWI YoY (%)", showgrid=False),
    )

    if not df.empty:
        from datetime import datetime
        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 12, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
        # Add 50 line for diffusion
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="#94a3b8",
            opacity=0.5,
            annotation_text="50",
            annotation_position="bottom right",
        )

    return fig


def OecdCliDiffusionIndex_Emerging() -> go.Figure:
    """OECD CLI Diffusion Index Emerging Market"""
    OECD_CLI_EM_CODES = [
        "TUR.LOLITOAA.STSA:PX_LAST",
        "IND.LOLITOAA.STSA:PX_LAST",
        "IDN.LOLITOAA.STSA:PX_LAST",
        "CHN.LOLITOAA.STSA:PX_LAST",
        "KOR.LOLITOAA.STSA:PX_LAST",
        "BRA.LOLITOAA.STSA:PX_LAST",
        "ESP.LOLITOAA.STSA:PX_LAST",
        "ITA.LOLITOAA.STSA:PX_LAST",
        "MEX.LOLITOAA.STSA:PX_LAST",
    ]

    try:
        # 1. Calculate Diffusion Index
        data = (
            MultiSeries(
                **{
                    k.replace(".LOLITOAA.STSA:PX_LAST", ""): Series(k)
                    for k in OECD_CLI_EM_CODES
                }
            )
            .resample("ME")
            .ffill()
        )

        ff = data.diff().dropna()
        ff = (ff > 0) * 1
        # Multiply by 100 to make it comparable to YoY % and standard diffusion index
        diffusion = ff.sum(axis=1).div(ff.count(axis=1)) * 100

        diffusion = (
            MonthEndOffset(diffusion.to_frame(), 3).iloc[:, 0].resample("W-Fri").ffill()
        )
        diffusion.name = "OECD CLI Diffusion Index Emerging (3M Lead)"

        # 2. Calculate Cycle
        diffusion_cycle = Cycle(diffusion.iloc[-52 * 10 :])
        diffusion_cycle.name = "Cycle"

        # 3. Fetch MSCI Emerging Market YoY
        # User requested naming 891800 (or 891700 typo) as "MSCI Emerging Market YoY (%)"
        msci = (
            Series("891800:FG_TOTAL_RET_IDX")
            .resample("W-Fri")
            .ffill()
            .pct_change(52)
            .mul(100)
        )
        msci.name = "MSCI Emerging Market YoY (%)"

        # Combine for alignment if needed, though they are already time series
        # Using a DataFrame to ensure index alignment in plot
        df = pd.DataFrame(
            {
                "Diffusion": diffusion,
                "Cycle": diffusion_cycle,
                "MSCI EM YoY": msci,
            }
        )

    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Diffusion (Left)
    col1 = "Diffusion"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], "Diffusion (3M Lead)", ".2f"),
            mode="lines",
            line=dict(width=3, color="#f8fafc"),
            hovertemplate="Diffusion (3M Lead): %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Cycle (Left)
    col_cycle = "Cycle"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_cycle],
            name=get_value_label(df[col_cycle], "Cycle", ".2f"),
            mode="lines",
            line=dict(width=3, color="#ef4444"),  # Cycle usually bold
            hovertemplate="Cycle: %{y:.2f}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 3. MSCI EM YoY (Right)
    col2 = "MSCI EM YoY"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "MSCI Emerging Market YoY (%)", ".2f"),
            mode="lines",
            line=dict(width=2, color="#f59e0b"),  # Different color usually helps
            hovertemplate="MSCI EM YoY: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>OECD CLI Diffusion Index - Emerging</b>"),
        yaxis=dict(
            title="Diffusion Index (%) / Cycle",
            range=[0, 100],
            tickvals=[0, 20, 40, 50, 60, 80, 100],
        ),
        yaxis2=dict(title="MSCI Emerging Market YoY (%)", showgrid=False),
    )

    if not df.empty:
        from datetime import datetime
        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 12, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
        # Add 50 line for diffusion
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="#94a3b8",
            opacity=0.5,
            annotation_text="50",
            annotation_position="bottom right",
        )

    return fig


def OecdCliDiffusionIndex_Developed() -> go.Figure:
    """OECD CLI Diffusion Index Developed Market"""
    OECD_CLI_DM_CODES = [
        "USA.LOLITOAA.STSA:PX_LAST",
        "JPN.LOLITOAA.STSA:PX_LAST",
        "DEU.LOLITOAA.STSA:PX_LAST",
        "GBR.LOLITOAA.STSA:PX_LAST",
        "FRA.LOLITOAA.STSA:PX_LAST",
        "CAN.LOLITOAA.STSA:PX_LAST",
        "AUS.LOLITOAA.STSA:PX_LAST",
    ]

    try:
        # 1. Calculate Diffusion Index
        data = (
            MultiSeries(
                **{
                    k.replace(".LOLITOAA.STSA:PX_LAST", ""): Series(k)
                    for k in OECD_CLI_DM_CODES
                }
            )
            .resample("ME")
            .ffill()
        )

        ff = data.diff().dropna()
        ff = (ff > 0) * 1
        # Multiply by 100 to make it comparable to YoY % and standard diffusion index
        diffusion = ff.sum(axis=1).div(ff.count(axis=1)) * 100

        diffusion = (
            MonthEndOffset(diffusion.to_frame(), 3).iloc[:, 0].resample("W-Fri").ffill()
        )
        diffusion.name = "OECD CLI Diffusion Index Developed (3M Lead)"

        # 2. Calculate Cycle
        diffusion_cycle = Cycle(diffusion.iloc[-52 * 10 :])
        diffusion_cycle.name = "Cycle"

        # 3. Fetch MSCI World YoY
        # Assuming MXWO Index for MSCI World
        msci = (
            Series("990100:FG_TOTAL_RET_IDX")
            .resample("W-Fri")
            .ffill()
            .pct_change(52)
            .mul(100)
        )
        msci.name = "MSCI World YoY (%)"

        # Combine for alignment if needed, though they are already time series
        # Using a DataFrame to ensure index alignment in plot
        df = pd.DataFrame(
            {
                "Diffusion": diffusion,
                "Cycle": diffusion_cycle,
                "MSCI World YoY": msci,
            }
        )

    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Diffusion (Left)
    col1 = "Diffusion"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], "Diffusion (3M Lead)", ".2f"),
            mode="lines",
            line=dict(width=3, color="#f8fafc"),
            hovertemplate="Diffusion (3M Lead): %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Cycle (Left)
    col_cycle = "Cycle"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_cycle],
            name=get_value_label(df[col_cycle], "Cycle", ".2f"),
            mode="lines",
            line=dict(width=3, color="#ef4444"),  # Cycle usually bold
            hovertemplate="Cycle: %{y:.2f}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 3. MSCI World YoY (Right)
    col2 = "MSCI World YoY"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], "MSCI World YoY (%)", ".2f"),
            mode="lines",
            line=dict(width=2, color="#f59e0b"),  # Different color usually helps
            hovertemplate="MSCI World YoY: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>OECD CLI Diffusion Index - Developed</b>"),
        yaxis=dict(
            title="Diffusion Index (%) / Cycle",
            range=[0, 100],
            tickvals=[0, 20, 40, 50, 60, 80, 100],
        ),
        yaxis2=dict(title="MSCI World YoY (%)", showgrid=False),
    )

    if not df.empty:
        from datetime import datetime
        latest_date = df.index.max()
        start_date = datetime(latest_date.year - 12, 1, 1)
        fig.update_xaxes(range=[start_date, latest_date])
        # Add 50 line for diffusion
        fig.add_hline(
            y=50,
            line_dash="dash",
            line_color="#94a3b8",
            opacity=0.5,
            annotation_text="50",
            annotation_position="bottom right",
        )

    return fig