import dash
from dash import Output, Input, State, callback, html, dcc
import dash_mantine_components as dmc
from ix.misc import all_subclasses
from ix.bt.strategy import Strategy
from dash_iconify import DashIconify

dash.register_page(
    __name__,
    path="/strategy",
)


def layout():

    return html.Div(
        [
            dmc.Container(
                children=[
                    html.H1("Market Strategy Models"),
                    dmc.Select(
                        id="strategy-selection",
                        value="SectorRotationCESI",
                        data=[
                            strategy.__name__ for strategy in all_subclasses(Strategy)
                        ],
                        label="Market Strategy Model",
                        w=200,
                        leftSection=DashIconify(icon="radix-icons:magnifying-glass"),
                        clearable=True,
                    ),
                ],
                style={
                    "marginTop": 20,
                    "marginBottom": 20,
                },
            ),
            dmc.Container(id="strategy-content"),
        ]
    )


from ix.misc import all_subclasses


@callback(
    Output("strategy-content", "children"),
    Input("strategy-selection", "value"),
)
def render_content(select: str):

    import plotly.graph_objects as go

    fig = go.Figure()
    for strategy in all_subclasses(Strategy):
        v = strategy().book.v
        fig.add_trace(
            go.Scatter(
                x=v.index,
                y=v.values,
                name=strategy.__name__,
            )
        )
    return html.Div(
        dcc.Graph(figure=fig),
    )
