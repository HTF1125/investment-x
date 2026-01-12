import pandas as pd
import pandas_datareader.data as web
import datetime
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------
# 1. DATA INGESTION & ADVANCED CALCULATION
# ---------------------------------------------------------
def get_macro_data():
    # Fetch ample history for expanding median
    start = datetime.datetime(1997, 1, 1)
    end = datetime.datetime.now()

    # Fetch High Yield Spread and S&P 500 from FRED
    # BAMLH0A0HYM2: ICE BofA US High Yield Index Option-Adjusted Spread
    # SP500: S&P 500
    try:
        df = web.DataReader(['BAMLH0A0HYM2', 'SP500'], 'fred', start, end)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

    # Forward fill to handle weekends/holidays differences between series
    df = df.resample('D').ffill().dropna()

    # --- Calculations ---
    # 1. Historic Median (Expanding Window)
    df['Historic_Median'] = df['BAMLH0A0HYM2'].expanding().median()
    
    # 2. Momentum (3-Month Change) - approx 65 trading days or 90 calendar days
    df['Spread_Change_3M'] = df['BAMLH0A0HYM2'].diff(periods=90)

    # 3. Classify Regimes
    def classify_regime(row):
        is_wide = row['BAMLH0A0HYM2'] > row['Historic_Median']
        is_rising = row['Spread_Change_3M'] > 0
        
        if is_wide and not is_rising:
            return "Recovery", "Q1", "#28a745" # Green
        elif not is_wide and not is_rising:
            return "Growth", "Q2", "#17a2b8"   # Blue
        elif not is_wide and is_rising:
            return "Overheating", "Q3", "#ffc107" # Yellow
        elif is_wide and is_rising:
            return "Recession", "Q4", "#dc3545"   # Red
        else:
            return "Uncertain", "N/A", "#6c757d"

    # Apply classification
    # We use zip to return multiple columns efficiently
    df[['Regime', 'Quadrant', 'Color']] = df.apply(
        lambda x: pd.Series(classify_regime(x)), axis=1
    )
    
    return df.dropna()

# Load Data
df = get_macro_data()
current = df.iloc[-1]

# ---------------------------------------------------------
# 2. CHART GENERATION
# ---------------------------------------------------------

# --- A. Main Time Series Chart (Spread + SPX + Background Color) ---
def create_main_chart(df):
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add S&P 500 (Log Scale for long-term view)
    fig.add_trace(
        go.Scatter(x=df.index, y=df['SP500'], name="S&P 500", 
                   line=dict(color='gray', width=1), opacity=0.5),
        secondary_y=True,
    )
    
    # Add HY Spread
    fig.add_trace(
        go.Scatter(x=df.index, y=df['BAMLH0A0HYM2'], name="HY Spread",
                   line=dict(color='black', width=2)),
        secondary_y=False,
    )

    # Add Median
    fig.add_trace(
        go.Scatter(x=df.index, y=df['Historic_Median'], name="Historic Median",
                   line=dict(color='blue', dash='dot', width=1)),
        secondary_y=False,
    )

    # Add Regime Background Coloring
    # We create shapes for every day is computationally heavy, so we aggregate contiguous periods
    # For performance in Dash, we often skip full background shading or optimize it. 
    # Here is a simplified approach using a Heatmap strip at the bottom
    
    fig.update_layout(
        title="<b>Market Regime History</b>: HY Spread vs S&P 500",
        template="plotly_white",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450,
        hovermode="x unified"
    )
    
    fig.update_yaxes(title_text="HY Spread (%)", secondary_y=False)
    fig.update_yaxes(title_text="S&P 500 (Log)", type="log", secondary_y=True, showgrid=False)
    
    return fig

# --- B. Phase Diagram (Cycle Clock) ---
def create_phase_diagram(df):
    # Filter for the last 250 days (1 year) to show trajectory
    lookback = 252
    subset = df.tail(lookback).copy()
    
    current_median = subset['Historic_Median'].iloc[-1]
    
    fig = go.Figure()

    # Draw Quadrant Lines
    fig.add_vline(x=current_median, line_width=1, line_dash="dash", line_color="gray")
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")

    # Add Quadrant Labels
    annotations = [
        dict(x=current_median*1.2, y=-0.5, text="Growth (Q2)", showarrow=False, font=dict(color="blue", size=14)),
        dict(x=current_median*0.8, y=-0.5, text="Recovery (Q1)", showarrow=False, font=dict(color="green", size=14)),
        dict(x=current_median*1.2, y=0.5, text="Overheating (Q3)", showarrow=False, font=dict(color="orange", size=14)),
        dict(x=current_median*0.8, y=0.5, text="Recession (Q4)", showarrow=False, font=dict(color="red", size=14))
    ]
    # Note: Coordinates for labels are approximations; in a real app, dynamic positioning is better.
    # We use 'paper' or data coords. Here let's assume standard spread ranges.

    # Plot the Trail (Last Year)
    fig.add_trace(go.Scatter(
        x=subset['BAMLH0A0HYM2'], 
        y=subset['Spread_Change_3M'],
        mode='lines+markers',
        name='1Y Trajectory',
        marker=dict(
            size=6,
            color=subset.index.astype(int), # Gradient by time
            colorscale='Viridis',
            showscale=False
        ),
        line=dict(color='lightgray', width=1)
    ))

    # Highlight Current Point
    latest = subset.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[latest['BAMLH0A0HYM2']], 
        y=[latest['Spread_Change_3M']],
        mode='markers+text',
        name='Current',
        text=['CURRENT'],
        textposition="top center",
        marker=dict(size=15, color='red', symbol='star')
    ))

    fig.update_layout(
        title="<b>Macro Cycle Clock</b> (Spread vs. Momentum)",
        xaxis_title="Spread Level (Low ← → High)",
        yaxis_title="3M Change (Falling ← → Rising)",
        template="plotly_white",
        height=400,
        xaxis=dict(autorange="reversed") # Low spread is usually 'Good' (Right side) but standard X axis increases right. 
                                         # Verdad charts often put 'Wide' on left? Let's stick to standard math: 
                                         # Wide (High) is bad. 
    )
    
    # Fix X-Axis: Verdad usually implies Wide spreads are "bad" (Recession/Recovery). 
    # Let's keep standard: Right = Higher Spread (Wider).
    
    return fig

# ---------------------------------------------------------
# 3. DASH LAYOUT
# ---------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])

# Indicators Row
card_content_current = [
    dbc.CardHeader("Current Regime"),
    dbc.CardBody([
        html.H2(f"{current['Regime']}", className="card-title", style={"color": current['Color']}),
        html.H5(f"{current['Quadrant']}", className="card-subtitle"),
    ]),
]

card_content_spread = [
    dbc.CardHeader("HY Spread Level"),
    dbc.CardBody([
        html.H2(f"{current['BAMLH0A0HYM2']:.2f}%", className="card-title"),
        html.P(f"Median: {current['Historic_Median']:.2f}%", className="card-text"),
    ]),
]

card_content_momentum = [
    dbc.CardHeader("Spread Momentum (3M)"),
    dbc.CardBody([
        html.H2(f"{current['Spread_Change_3M']:+.2f} bps", className="card-title", 
                style={"color": "red" if current['Spread_Change_3M'] > 0 else "green"}),
        html.P("Positive = Tightening Conditions", className="card-text"),
    ]),
]

app.layout = dbc.Container([
    # -- Header --
    dbc.Row([
        dbc.Col(html.H1("Macro Regime Monitor", className="text-primary"), width=8),
        dbc.Col(html.H5(f"Last Updated: {current.name.strftime('%Y-%m-%d')}", className="text-muted text-end"), width=4),
    ], className="mt-4 mb-4"),

    html.Hr(),

    # -- Key Metrics Cards --
    dbc.Row([
        dbc.Col(dbc.Card(card_content_current, color="light", outline=True), width=4),
        dbc.Col(dbc.Card(card_content_spread, color="light", outline=True), width=4),
        dbc.Col(dbc.Card(card_content_momentum, color="light", outline=True), width=4),
    ], className="mb-4"),

    # -- Charts Row --
    dbc.Row([
        # Main Time Series
        dbc.Col(dcc.Graph(figure=create_main_chart(df)), width=8),
        # Cycle Clock
        dbc.Col(dcc.Graph(figure=create_phase_diagram(df)), width=4),
    ]),

    # -- Detailed Logic / Table --
    dbc.Row([
        dbc.Col([
            html.H4("Recent Regime Changes"),
            # Taking last 5 regime changes could be complex code, just showing recent data tail for now
            dbc.Table.from_dataframe(
                df[['BAMLH0A0HYM2', 'Spread_Change_3M', 'Regime', 'Quadrant']].tail(5).sort_index(ascending=False).reset_index(),
                striped=True, bordered=True, hover=True, size="sm"
            )
        ], width=12)
    ], className="mt-4"),

    # -- Strategy Reference --
    dbc.Row([
        dbc.Col(dbc.Alert([
            html.H5("Strategy Reference (Verdad Capital)", className="alert-heading"),
            html.P("This dashboard tracks the Verdad Capital 'Best Macro Indicator' strategy."),
            html.Hr(),
            html.Ul([
                html.Li(html.B("Recovery (Q1): Spread Wide & Falling → Buy Small Cap Value")),
                html.Li(html.B("Growth (Q2): Spread Narrow & Falling → Buy Equities & Oil")),
                html.Li(html.B("Overheating (Q3): Spread Narrow & Rising → Buy S&P 500 (Trend) or Commodities")),
                html.Li(html.B("Recession (Q4): Spread Wide & Rising → Buy Treasurys & Gold")),
            ])
        ], color="info"), width=12)
    ], className="mt-4 mb-5")

], fluid=True)

if __name__ == '__main__':
    app.run_server(debug=True)