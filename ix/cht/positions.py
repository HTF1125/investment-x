import plotly.graph_objects as go
import pandas as pd
from ix.db.query import Series, MultiSeries, StandardScalar
from .style import apply_academic_style, add_zero_line, get_value_label, get_color


def PositionsCrowdedness() -> go.Figure:
    """Crowdedness in major assets based on CFTC positioning."""

    # Window of 156 weeks (3 years) for the StandardScalar normalization
    lookback = 156

    try:
        # Define the base data dict
        data_dict = {
            "S&P500": StandardScalar(
                Series("CFTNCLOI%ALLS5C3512CMEOF_US:PX_LAST")
                .sub(Series("CFTNCSOI%ALLS5C3512CMEOF_US:PX_LAST"))
                .ffill()
                .resample("W-Fri")
                .ffill(),
                lookback,
            ),
            "Gold": StandardScalar(
                Series("CFTNCLOI%ALLGOLDCOMOF_US:PX_LAST")
                .sub(Series("CFTNCSOI%ALLGOLDCOMOF_US:PX_LAST"))
                .ffill()
                .resample("W-Fri")
                .ffill(),
                lookback,
            ),
            "Commodities": StandardScalar(
                Series("CFTNCLOI%ALLDJUBSERCBOTOF_US:PX_LAST")
                .sub(Series("CFTNCSOI%ALLDJUBSERCBOTOF_US:PX_LAST"))
                .ffill()
                .resample("W-Fri")
                .ffill(),
                lookback,
            ),
            "USD": StandardScalar(
                Series("CFTNCLOI%ALLJUSDNYBTOF_US:PX_LAST")
                .sub(Series("CFTNCSOI%ALLJUSDNYBTOF_US:PX_LAST"))
                .ffill()
                .resample("W-Fri")
                .ffill(),
                lookback,
            ),
            "UST10Y": StandardScalar(
                Series("CFTNCLOI%ALLTN10YCBOTOF_US:PX_LAST")
                .sub(Series("CFTNCSOI%ALLTN10YCBOTOF_US:PX_LAST"))
                .ffill()
                .resample("W-Fri")
                .ffill(),
                lookback,
            ),
        }

        # Create MultiSeries, compute rolling mean, and slice last 3 years
        df = MultiSeries(**data_dict).rolling(4).mean().iloc[-52 * 3 :]

    except Exception as e:
        raise Exception(f"Error fetching data for PositionsCrowdedness: {e}")

    fig = go.Figure()

    for col in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                mode="lines",
                hovertemplate=f"{col}: %{{y:.2f}}<extra></extra>",
            )
        )

    # Add Upper/Lower bounds
    # "Upper Bound (+2.0): Label as "Threshold: Crowded Long / Reversal Risk.""
    fig.add_hline(
        y=2.0,
        line_dash="dash",
        line_color=get_color("Secondary"),
        line_width=2,
        annotation_text="Threshold (+2.0): Crowded Long",
        annotation_position="top left",
        layer="below",
    )

    # "Lower Bound (-2.0): Label as "Threshold: Crowded Short / Squeeze Potential.""
    fig.add_hline(
        y=-2.0,
        line_dash="dash",
        line_color=get_color("Secondary"),
        line_width=2,
        annotation_text="Threshold (-2.0): Crowded Short",
        annotation_position="bottom left",
        layer="below",
    )

    apply_academic_style(fig)
    add_zero_line(fig)

    fig.update_layout(
        title=dict(text="<b>CFTC Positioning Crowdedness (Z-Score, 3Y Lookback)</b>"),
        yaxis=dict(title="Z-Score"),
    )

    return fig
