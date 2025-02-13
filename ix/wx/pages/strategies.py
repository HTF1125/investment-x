import dash
from dash import dcc, html, Input, Output, callback, register_page
from ix.bt import strategy  # Import your strategy module

# Register this file as a page at '/strategies'
register_page(__name__, path="/strategies", title="Strategies Performance")

# Get the list of strategy classes.
strategy_classes = strategy.all_strategies()

# Build dropdown options and a mapping from strategy name to class.
strategy_options = [{"label": s.__name__, "value": s.__name__} for s in strategy_classes]
strategy_mapping = {s.__name__: s for s in strategy_classes}

# Define the layout for the page.
layout = html.Div(
    children=[
        html.H1("Strategy Performance"),
        dcc.Dropdown(
            id="strategy-dropdown",
            options=strategy_options,
            value=strategy_options[0]["value"] if strategy_options else None,
            clearable=False,
            style={"width": "300px", "margin": "20px auto"},
        ),
        dcc.Graph(id="strategy-graph"),
    ],
    style={"textAlign": "center"},
)

@callback(
    Output("strategy-graph", "figure"),
    Input("strategy-dropdown", "value"),
)
def update_graph(selected_strategy_name):
    if not selected_strategy_name:
        # If no strategy is selected, return an empty figure.
        import plotly.graph_objects as go
        return go.Figure()

    # Retrieve the strategy class for the selected strategy.
    strat_class = strategy_mapping.get(selected_strategy_name)
    if not strat_class:
        import plotly.graph_objects as go
        return go.Figure()

    # Instantiate the strategy and run the simulation.
    strat_instance = strat_class()

    # Generate and return the Plotly figure.
    # (Assumes your `plot` method supports `return_fig=True`.)
    return strat_instance.plot()
