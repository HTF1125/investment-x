import dash
from dash import html, dcc
from dash import Output, Input, State, callback, html
from ix.bt.regime import Regime
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from ix.db import get_pxs
import plotly.graph_objects as go
from ix.misc import all_subclasses
from ix import db
from ix.core import performance_by_state
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd

dash.register_page(
    __name__,
    path="/regime",
)


def layout():

    regimes = db.Regime.find_all().run()

    return html.Div(
        [
            dmc.Container(
                children=[
                    html.H1("Market Regime Models"),
                    dmc.Select(
                        id="regime-selection",
                        value=regimes[0].code,
                        data=[regime.code for regime in regimes],
                        label="Market Regime Model",
                        w=200,
                        leftSection=DashIconify(icon="radix-icons:magnifying-glass"),
                        clearable=True,
                    ),
                    html.Div(
                        [
                            dmc.Tabs(
                                [
                                    dmc.TabsList(
                                        [
                                            dmc.TabsTab(
                                                "Performance by State", value="1"
                                            ),
                                            dmc.TabsTab("Performances", value="2"),
                                        ]
                                    ),
                                ],
                                id="tabs-example",
                                value="1",
                            ),
                            dcc.Loading(
                                html.Div(
                                    id="regime-graph-container",
                                    children=dmc.Container(
                                        id="tabs-content",
                                        style={"paddingTop": 10},
                                    ),
                                ),
                            ),
                        ]
                    ),
                ],
                style={
                    "marginTop": 20,
                    "marginBottom": 20,
                },
            ),
        ]
    )


@callback(
    Output("tabs-content", "children"),
    Input("tabs-example", "value"),
    Input("regime-selection", "value"),
)
def render_content(active, regime_model):
    pxs = get_pxs(["SPY", "TLT", "GLD"]).dropna()

    regime = db.Regime.find_one({"code": regime_model}).run()
    if regime is None:
        return

    states = pd.Series(regime.data, name="States")
    states.index = pd.to_datetime(states.index)

    if active == "1":

        p = performance_by_state(states=states, pxs=pxs)

        fig = go.Figure()
        for c in p:
            fig.add_trace(
                trace=go.Bar(
                    x=p.index,
                    y=p[c].values,
                    name=c,
                )
            )

        return dmc.Container(
            dcc.Graph(figure=fig),
        )

    else:

        columns_to_plot = list(pxs.columns)
        num_subplots = len(columns_to_plot)

        fig = make_subplots(
            rows=num_subplots,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.10,
            subplot_titles=columns_to_plot,
        )

        unique_states = states.unique()

        color_palette = {
            state: color
            for state, color in zip(unique_states, px.colors.qualitative.Light24)
        }
        data = pd.concat([pxs, states], axis=1)
        data[pxs.columns] = data[pxs.columns].ffill()
        data = data.dropna()
        data[pxs.columns] = data[pxs.columns].pct_change().shift(-1)
        data = data.dropna()

        # Add traces for each subplot
        for i, col in enumerate(columns_to_plot, start=1):
            d = data[["States", col]]

            # Plot colored markers based on the regime states
            for state in unique_states:
                state_df = d[d["States"] == state].dropna()

                if state_df.empty:
                    continue
                # Show legend only in the first subplot and link the same state to each subplot
                show_legend = i == 1
                fig.add_trace(
                    go.Bar(
                        x=state_df.index,
                        y=state_df[col],
                        # mode="markers",
                        name=state,
                        legendgroup=state,  # Group traces for the same state
                        showlegend=show_legend,  # Only show legend for the first subplot
                        marker=dict(color=color_palette[state]),  # Use consistent color
                    ),
                    row=i,
                    col=1,
                )

        # Update layout to position the legend at the top
        fig.update_layout(
            title_text=regime_model,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            hovermode="x unified",
            height=300 * num_subplots,  # Adjust height based on the number of subplots
        )

        # Apply y-axis formatting to all subplots
        for i in range(1, num_subplots + 1):
            fig.update_yaxes(tickformat=".2%", row=i, col=1)

    return html.Div(
        dcc.Graph(figure=fig),
    )
