import dash
from dash import html, dcc
from dash import Output, Input, callback, html
from ix.bt.regime import Regime
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import plotly.graph_objects as go


dash.register_page(
    __name__,
    path="/",
    order=1,
)


def layout():

    codes = [
        "SPX Index",
        "INDU Index",
        "CCMP Index",
        "RTY Index",
        "SX5E Index",
        "UKX Index",
        "NKY Index",
        "KOSPI Index",
        "SHCOMP Index",
    ]


    

    return html.Div("Welcome")
