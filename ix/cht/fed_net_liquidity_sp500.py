from ix.db import Series
from ix.dash.settings import theme
from ix.cht import apply_layout
from ix.cht import apply_axes
import plotly.graph_objects as go
import pandas as pd


def get_fed_net_liquidity_series() -> pd.Series:
    """
    Calculate the Fed Net Liquidity in trillions USD.
    Net Liquidity = Fed Assets - Treasury General Account - Reverse Repo
    All series are resampled to weekly (Wednesday) and forward-filled.
    """
    # Fetch data
    asset_mil = Series("WALCL")  # Fed assets, millions USD
    treasury_bil = Series("WTREGEN")  # Treasury General Account, billions USD
    repo_bil = Series("RRPONTSYD")  # Reverse Repo, billions USD

    # Convert to trillions
    asset = asset_mil / 1_000_000
    treasury = treasury_bil / 1_000
    repo = repo_bil / 1_000

    # Combine and resample
    df = pd.concat({"Fed Assets": asset, "TGA": treasury, "RRP": repo}, axis=1)
    weekly = df.resample("W-WED").last().ffill()

    # Calculate net liquidity
    weekly["Net Liquidity (T)"] = weekly["Fed Assets"] - weekly["TGA"] - weekly["RRP"]
    return weekly["Net Liquidity (T)"].dropna()


def fed_net_liquidity_vs_sp500():
    """
    Plot Fed Net Liquidity YoY % vs S&P 500 YoY %.
    """
    # Calculate YoY changes
    net_liquidity = get_fed_net_liquidity_series().pct_change(52).dropna()
    sp500 = Series("SPX Index:PX_LAST", freq="W").pct_change(52).dropna()

    # Get latest values for legend
    latest_liquidity = net_liquidity.iloc[-1] if not net_liquidity.empty else None
    latest_sp500 = sp500.iloc[-1] if not sp500.empty else None

    fig = go.Figure()

    # Fed Net Liquidity trace
    fig.add_trace(
        go.Scatter(
            x=net_liquidity.index,
            y=net_liquidity.values,
            name=(
                f"Fed Net Liquidity YoY ({latest_liquidity:.2%})"
                if latest_liquidity is not None
                else "Fed Net Liquidity YoY"
            ),
            line=dict(color=theme.primary, width=3),
            hovertemplate="<b>Fed Net Liquidity YoY</b>: %{y:.2%}<extra></extra>",
        )
    )

    # S&P 500 trace
    fig.add_trace(
        go.Scatter(
            x=sp500.index,
            y=sp500.values,
            name=(
                f"S&P 500 YoY ({latest_sp500:.2%})"
                if latest_sp500 is not None
                else "S&P 500 YoY"
            ),
            yaxis="y1",
            line=dict(color=theme.warning, width=3),
            hovertemplate="<b>S&P 500 YoY</b>: %{y:.2%}<extra></extra>",
        )
    )

    # Apply layout and axes
    apply_layout(fig, "Fed Net Liquidity & S&P 500 YoY")
    apply_axes(
        fig,
        y_title="Fed Net Liquidity YoY (%)",
        y_tickformat=".0%",
        y2_title="S&P 500 YoY (%)",
        y2_tickformat=".0%",
        y_range=[-1, 1],
        show_y2_grid=False,
    )

    # Optionally, add a band for recession periods or highlight recent data
    # (Not implemented here, but could be added for further improvement)

    # Show the figure with the new width prop
    return fig
