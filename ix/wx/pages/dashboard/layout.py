from dash import html, dcc, register_page, callback_context, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, MATCH
from ix.db.query import MultiSeries, Series

# 페이지 등록
register_page(__name__, path="/", title="Dashboard", name="Dashboard")

# 레이아웃: Bootstrap 그리드로 3열 혹은 반응형 배치
layout = dbc.Textarea(id="ff")

