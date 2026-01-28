import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
from sqlalchemy import text as sqltext

# Assuming these imports exist in your environment
from ix.db.query import Series, MultiSeries
from ix.core import ContributionToGrowth
from ix.db.query import StandardScalar, Cycle, MonthEndOffset, NumPositivePercentByRow
from ix.db.conn import ensure_connection, conn

# ==========================================
# 1. SHARED UTILITIES & BASE CLASS
# ==========================================

def save_chart_json(name, fig, description=None, category=None, tags=None):
    """Saves the Plotly figure to the database."""
    try:
        if not ensure_connection():
            st.warning(f"DB connection not available; skipping save for {name}.")
            return
        fig_json = fig.to_json()
        if tags is not None and not isinstance(tags, str):
            tags = json.dumps(tags)
        
        upsert_sql = sqltext("""
            INSERT INTO charts (name, figure, description, category, tags, updated_at)
            VALUES (:name, CAST(:figure AS jsonb), :description, :category, CAST(:tags AS jsonb), now())
            ON CONFLICT (name) DO UPDATE SET
                figure = EXCLUDED.figure,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                tags = EXCLUDED.tags,
                updated_at = now();
        """)
        
        with conn.engine.begin() as connection:
            connection.execute(upsert_sql, {
                "name": name, "figure": fig_json, "description": description, 
                "category": category, "tags": tags
            })
    except Exception as exc:
        st.warning(f"Failed to save chart '{name}' to DB: {exc}")

class BaseChart:
    """Parent class containing shared styling and rendering logic."""
    def __init__(self, title):
        self.title = title
        self.df = None
        self.fig = None
        self.colors = ["#2a7fff", "#ff00b8", "#2c2f7a", "#00d6c6", "#ff8c00", "#7fff00"]

    def apply_layout(self, fig, legend_cols=4):
        fig.update_layout(
            width=1000,
            height=500,
            template="plotly_dark",
            margin=dict(l=50, r=150, t=60, b=50), # Increased Right Margin for labels
            title=dict(text=self.title, x=0.5, xanchor="center", y=0.96, yanchor="top"),
            legend=dict(
                orientation="h", x=0.01, xanchor="left", y=1.02, yanchor="bottom",
                bgcolor="rgba(0,0,0,0)", borderwidth=0
            ),
            hovermode="x unified",
        )
        # Global Grid Styling
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)", griddash="dot")
        fig.update_xaxes(tickformat="%Y-%m-%d")

    def add_label(self, fig, x, y, text, color, yaxis="y", text_color="white", xshift=10, yshift=0, yanchor="middle"):
        fig.add_annotation(
            x=x, y=y, xref="x", yref=yaxis,
            text=text, showarrow=False,
            xanchor="left", yanchor=yanchor,
            xshift=xshift, yshift=yshift,
            bgcolor=color, bordercolor=color,
            font=dict(color=text_color, size=11, family="Arial")
        )
    
    def extend_xaxis(self, fig, weeks=26):
        """Adds empty space to the right of the chart for labels."""
        if self.df is not None and not self.df.empty:
            start = self.df.index[0]
            end = self.df.index[-1] + pd.Timedelta(weeks=weeks)
            fig.update_xaxes(range=[start, end])

    def render(self):
        """Standard render pipeline: Build -> Plot -> Save."""
        if self.fig is None:
            if hasattr(self, 'plot'):
                self.plot()
            else:
                st.error(f"Chart {self.title} has no plot method.")
                return
        
        st.plotly_chart(self.fig, use_container_width=False)
        save_chart_json(self.title, self.fig)


# ==========================================
# 2. CHART IMPLEMENTATIONS
# ==========================================

class FinancialConditionsChart(BaseChart):
    def __init__(self):
        super().__init__("Financial Conditions")

    def build_data(self):
        # ... (Data Fetching Logic) ...
        fci_rates_credit = MultiSeries(**{
            "Treasury10Y": StandardScalar(-Series("TRYUS10Y:PX_YTM", freq="W-Fri").ffill(), 156),
            "Mortgage": StandardScalar(-Series("MORTGAGE30US", freq="W-Fri").ffill(), 156),
            "HY Spread": StandardScalar(-Series("BAMLH0A0HYM2:PX_LAST", freq="W-Fri").ffill(), 156),
        }).ffill().mean(axis=1)

        fci_equities = MultiSeries(**{
            "S&P500": StandardScalar(Series("SPX Index:PX_LAST", freq="W-Fri").ffill(), 156),
            "Nasdaq": StandardScalar(Series("CCMP Index:PX_LAST", freq="W-Fri").ffill(), 156),
            "Small/Large": StandardScalar(Series("RTY INDEX:PX_LAST", freq="W-Fri").ffill() / Series("SPX INDEX:PX_LAST", freq="W-Fri").ffill(), 156),
        }).ffill().mean(axis=1)

        fci_fx_commodity = MultiSeries(**{
            "Dollar": StandardScalar(-Series("DXY Index:PX_LAST", freq="W-Fri").ffill(), 156),
            "WTI": StandardScalar(-Series("WTI Comdty:PX_LAST", freq="W-Fri").ffill(), 156),
        }).ffill().mean(axis=1)

        fci_risk = StandardScalar(-Series("VIX INDEX:PX_LAST", freq="W-Fri").ffill(), 156)

        fci_proprietary = MultiSeries(**{
            "Rates/Credit": fci_rates_credit, "Equities": fci_equities,
            "FX/Comm": fci_fx_commodity, "Risk": fci_risk
        }).mean(axis=1).ewm(span=26).mean().mul(100)

        # Re-calc for Cycle
        fci_equities_cycle = MultiSeries(**{
            "S&P500": StandardScalar(Series("SPX Index:PX_LAST", freq="W-Fri").ffill(), 156),
            "Nasdaq": StandardScalar(Series("CCMP Index:PX_LAST", freq="W-Fri").ffill(), 156),
            "Small/Large": StandardScalar(Series("RTY INDEX:PX_LAST", freq="W-Fri").ffill() / Series("SPX INDEX:PX_LAST", freq="W-Fri").ffill(), 156),
            "Cyc/Def": StandardScalar(Series("XLY INDEX:PX_LAST", freq="W-Fri").ffill() / Series("XLP INDEX:PX_LAST", freq="W-Fri").ffill(), 156),
        }).ffill().mean(axis=1)

        fci_cycle_base = MultiSeries(**{
            "Rates": fci_rates_credit, "Eq": fci_equities_cycle, "FX": fci_fx_commodity, "Risk": fci_risk
        }).mean(axis=1).ewm(span=26).mean().mul(100)
        
        fci_cycle = Cycle(fci_cycle_base.dropna().iloc[-52*10:], 52*10)
        fci_fed_scaled = Series("USSU8083177:PX_LAST", freq="W-Fri").ffill().mul(-50)
        spx_yoy = Series("SPX INDEX:PX_LAST", freq="W-Fri").pct_change(52).mul(100)

        self.df = MultiSeries(**{
            "FCI (Proprietary)": fci_proprietary,
            "Cycle": fci_cycle,
            "FCI (Fed Scaled)": fci_fed_scaled,
            "S&P500 YoY (%)": spx_yoy,
        }).dropna(how="all").iloc[-52*10:]
        return self.df

    def plot(self):
        if self.df is None: self.build_data()
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        configs = [
            ("FCI (Proprietary)", "#ff00b8", False),
            ("Cycle", "#2a7fff", False),
            ("FCI (Fed Scaled)", "#2c2f7a", False),
            ("S&P500 YoY (%)", "#00d6c6", True)
        ]

        last_x = self.df.index[-1]

        for col, color, is_sec in configs:
            fig.add_trace(
                go.Scatter(
                    x=self.df.index, y=self.df[col], name=col,
                    line=dict(width=2, color=color),
                    hovertemplate="%{y:.2f}"
                ), secondary_y=is_sec
            )
            val = self.df[col].iloc[-1]
            self.add_label(fig, last_x, val, f"{val:.1f}", color, "y2" if is_sec else "y")

        fig.add_hline(y=0, line_color="#888888", line_width=1)
        self.apply_layout(fig)
        self.extend_xaxis(fig, weeks=50) # Buffer for labels
        self.fig = fig
        return fig


class OecdCliDiffusionChart(BaseChart):
    def __init__(self):
        super().__init__("OECD CLI Diffusion Index")

    def build_data(self):
        countries = ["USA", "TUR", "IND", "IDN", "CHN", "KOR", "BRA", "AUS", "CAN", "DEU", "ESP", "FRA", "GBR", "ITA", "JPN", "MEX"]
        cli = MultiSeries(**{x: Series(f"{x}.LOLITOAA.STSA:PX_LAST", freq="ME") for x in countries})
        diffusion = MonthEndOffset(NumPositivePercentByRow(cli.diff().dropna(how="all")), 3)
        cycle = Cycle(diffusion)
        acwi_yoy = Series("ACWI US EQUITY:PX_LAST", freq="ME").ffill().pct_change(12).mul(100).dropna()

        self.df = MultiSeries(**{
            "OECD CLI Diffusion (3M Lead)": diffusion,
            "Cycle": cycle,
            "ACWI YoY (%)": acwi_yoy,
        }).dropna(how="all").iloc[-12*10:]
        return self.df

    def plot(self):
        if self.df is None: self.build_data()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        configs = [
            ("OECD CLI Diffusion (3M Lead)", "#ff00b8", False),
            ("Cycle", "#2a7fff", False),
            ("ACWI YoY (%)", "#2c2f7a", True)
        ]

        last_x = self.df.index[-1]
        for col, color, is_sec in configs:
            fig.add_trace(go.Scatter(x=self.df.index, y=self.df[col], name=col, line=dict(color=color, width=2.5), hovertemplate="%{y:.2f}"), secondary_y=is_sec)
            self.add_label(fig, last_x, self.df[col].iloc[-1], f"{self.df[col].iloc[-1]:.1f}", color, "y2" if is_sec else "y")

        fig.add_hline(y=50, line_color="#888888", line_width=1, line_dash="dash") # 50 line for Diffusion
        self.apply_layout(fig)
        self.extend_xaxis(fig, weeks=20)
        self.fig = fig
        return fig


class GlobalMoneySupplyChart(BaseChart):
    def __init__(self):
        super().__init__("Global Money Supply")

    def build_data(self):
        countries = ["US", "EUZ", "JP", "CN", "KR", "GB"]
        # Helper to sum series
        def get_sum_trillion(suffix):
            data = {c: Series(f"{c}.{suffix}:PX_LAST", scale=1, ccy="USD", freq="D").ffill() for c in countries}
            # Adjust specific tickers if needed (e.g. EU vs EUZ)
            if "US" in data: data["US"] = Series("US.CBASSET:PX_LAST" if suffix=="CBASSET" else "US.MAM2:PX_LAST", scale=1, ccy="USD", freq="D").ffill() 
            return MultiSeries(**data).ffill().sum(axis=1).div(10**12).resample("W-Fri").last()

        self.df = MultiSeries(**{
            "Global CB Assets ($Tr)": get_sum_trillion("CBASSET"),
            "Global Money Supply ($Tr)": get_sum_trillion("MAM2"),
        }).dropna(how="all").iloc[-52*10:]
        return self.df

    def plot(self):
        if self.df is None: self.build_data()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        last_x = self.df.index[-1]
        
        # CB Assets
        col1 = "Global CB Assets ($Tr)"
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df[col1], name=col1, line=dict(color="#ff00b8", width=2.5), hovertemplate="%{y:.2f}T"), secondary_y=False)
        self.add_label(fig, last_x, self.df[col1].iloc[-1], f"{self.df[col1].iloc[-1]:.1f}T", "#ff00b8", "y")

        # Money Supply
        col2 = "Global Money Supply ($Tr)"
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df[col2], name=col2, line=dict(color="#2a7fff", width=2.5), hovertemplate="%{y:.2f}T"), secondary_y=True)
        self.add_label(fig, last_x, self.df[col2].iloc[-1], f"{self.df[col2].iloc[-1]:.1f}T", "#2a7fff", "y2")

        self.apply_layout(fig)
        self.extend_xaxis(fig, weeks=50)
        self.fig = fig
        return fig


class BaseContributionChart(BaseChart):
    """Abstract base for stacked bar charts (M2, CB Assets)."""
    def __init__(self, title, series_suffix, weeks_back=260):
        super().__init__(title)
        self.series_suffix = series_suffix
        self.weeks_back = weeks_back

    def build_data(self):
        # Map country codes to tickers accurately
        tickers = {
            "US": f"US.{self.series_suffix}:PX_LAST",
            "EU": f"EUZ.{self.series_suffix}:PX_LAST",
            "JP": f"JP.{self.series_suffix}:PX_LAST",
            "CN": f"CN.{self.series_suffix}:PX_LAST",
            "KR": f"KR.{self.series_suffix}:PX_LAST",
            "GB": f"GB.{self.series_suffix}:PX_LAST",
        }
        series_dict = {k: Series(v, scale=1, ccy="USD", freq="D").ffill() for k, v in tickers.items()}
        
        self.df = (
            ContributionToGrowth(
                MultiSeries(**series_dict).ffill().resample("W-Fri").last().ffill(),
                52
            ).iloc[-self.weeks_back:].dropna(how="all")
        )
        return self.df

    def plot(self):
        if self.df is None: self.build_data()
        fig = go.Figure()
        
        last_row = self.df.iloc[-1]
        last_date = self.df.index[-1]
        pos_cum, neg_cum = 0, 0

        for i, col in enumerate(self.df.columns):
            color = self.colors[i % len(self.colors)]
            val = self.df[col]
            last_val = last_row[col]

            fig.add_trace(go.Bar(
                x=self.df.index, y=val, name=col, marker_color=color,
                hovertemplate="%{y:.2f}%"
            ))

            # Stack Logic
            if last_val >= 0:
                y_pos = pos_cum + (last_val / 2)
                pos_cum += last_val
            else:
                y_pos = neg_cum + (last_val / 2)
                neg_cum += last_val
            
            # Add Component Label
            if abs(last_val) > 0.1: # Threshold to show label
                txt_col = "black" if i == 5 else "white" # High contrast for bright green
                self.add_label(fig, last_date, y_pos, f"{last_val:.1f}%", color, text_color=txt_col, xshift=15)

        # Add Total Label (Top Right Paper Coords)
        total_val = last_row.sum()
        fig.add_annotation(
            xref="paper", yref="paper", x=0.98, y=0.98,
            text=f"Total: {total_val:.1f}%", showarrow=False,
            xanchor="right", yanchor="top",
            bgcolor="#ffffff", bordercolor="#ffffff",
            font=dict(color="black", size=14, weight="bold"), borderpad=6
        )

        fig.update_layout(barmode="relative")
        fig.add_hline(y=0, line_color="#888888", line_width=1)
        self.apply_layout(fig)
        self.extend_xaxis(fig, weeks=12) # Shorter buffer for bars
        self.fig = fig
        return fig

class GlobalM2ContributionChart(BaseContributionChart):
    def __init__(self):
        super().__init__("Global M2 YoY - Contribution", "MAM2")

class GlobalCbAssetContributionChart(BaseContributionChart):
    def __init__(self):
        super().__init__("Global Central Bank Asset YoY - Contribution", "CBASSET")


class GlobalMoneySupplyYoYChart(BaseChart):
    def __init__(self):
        super().__init__("Global Money Supply YoY")

    def build_data(self):
        def get_yoy_sum(suffix):
            tickers = {
                "US": f"US.{suffix}:PX_LAST", "EU": f"EUZ.{suffix}:PX_LAST",
                "JP": f"JP.{suffix}:PX_LAST", "CN": f"CN.{suffix}:PX_LAST",
                "KR": f"KR.{suffix}:PX_LAST", "GB": f"GB.{suffix}:PX_LAST"
            }
            series = {k: Series(v, scale=1, ccy="USD", freq="D").ffill() for k,v in tickers.items()}
            return MultiSeries(**series).ffill().sum(axis=1).div(10**12).resample("W-Fri").last().pct_change(52).mul(100)

        self.df = MultiSeries(**{
            "Global CB Asset YoY (%)": get_yoy_sum("CBASSET"),
            "Global M2 YoY (%)": get_yoy_sum("MAM2"),
        }).dropna(how="all").iloc[-52*10:]
        return self.df

    def plot(self):
        if self.df is None: self.build_data()
        fig = go.Figure()
        
        configs = [
            ("Global CB Asset YoY (%)", "#ff00b8"),
            ("Global M2 YoY (%)", "#2a7fff")
        ]
        
        last_x = self.df.index[-1]
        for col, color in configs:
            fig.add_trace(go.Scatter(
                x=self.df.index, y=self.df[col], name=col,
                mode="lines", line=dict(width=2.5, color=color),
                hovertemplate="%{y:.2f}%"
            ))
            self.add_label(fig, last_x, self.df[col].iloc[-1], f"{self.df[col].iloc[-1]:.1f}%", color)

        fig.add_hline(y=0, line_color="#888888", line_width=1)
        self.apply_layout(fig)
        self.extend_xaxis(fig, weeks=50)
        self.fig = fig
        return fig

# ==========================================
# 3. BASE LONG TERM CYCLE
# ==========================================

class BaseLongTermCycleChart(BaseChart):
    def __init__(self, title, price_ticker, color):
        super().__init__(title)
        self.price_ticker = price_ticker
        self.color = color

    def build_data(self):
        price = Series(self.price_ticker, scale=1, ccy="USD", freq="D").ffill()
        yoy = price.pct_change(252).mul(100)
        cycle = (yoy - yoy.rolling(252*3).mean()) / yoy.rolling(252*3).std()
        self.df = MultiSeries(**{"Price": price, "YoY": yoy, "Cycle": cycle}).dropna().iloc[-252*20:]
        return self.df

    def plot(self):
        if self.df is None: self.build_data()

        if self.df is None or self.df.empty:
            st.warning(f"No data available for {self.title} (Check data availability or history length)")
            self.fig = go.Figure()
            return self.fig

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
            subplot_titles=("Price (Log)", "YoY Growth (%)", "Cycle (Z-Score)"),
            row_heights=[0.4, 0.3, 0.3]
        )
        last_x = self.df.index[-1]
        
        # Plot Logic
        # 1. Price
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["Price"], name="Price", line=dict(color=self.color)), row=1, col=1)
        fig.update_yaxes(type="log", row=1, col=1, gridcolor="#333")
        self.add_label(fig, last_x, self.df["Price"].iloc[-1], f"{self.df['Price'].iloc[-1]:,.2f}", self.color, yaxis="y")
        
        # 2. YoY
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["YoY"], name="YoY", line=dict(color=self.color)), row=2, col=1)
        fig.add_hline(y=0, line_color="#666", row=2, col=1)
        self.add_label(fig, last_x, self.df["YoY"].iloc[-1], f"{self.df['YoY'].iloc[-1]:.1f}%", self.color, yaxis="y2")
        
        # 3. Cycle
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["Cycle"], name="Cycle", fill='tozeroy', line=dict(color=self.color)), row=3, col=1)
        fig.add_hline(y=0, line_color="#666", row=3, col=1)
        self.add_label(fig, last_x, self.df["Cycle"].iloc[-1], f"{self.df['Cycle'].iloc[-1]:.2f}", self.color, yaxis="y3")

        self.apply_layout(fig)
        fig.update_layout(showlegend=False) # Legend redundant here
        self.extend_xaxis(fig, weeks=100)
        self.fig = fig
        return fig

class LongTermCycleSPX(BaseLongTermCycleChart):
    def __init__(self): super().__init__("Long Term Cycles - S&P500", "SP50:PX_LAST", "#2a7fff")

class LongTermCycleUSD(BaseLongTermCycleChart):
    def __init__(self): super().__init__("Long Term Cycles - USD", "DXY INDEX:PX_LAST", "#2c2f7a")

class LongTermCycleGold(BaseLongTermCycleChart):
    def __init__(self): super().__init__("Long Term Cycles - Gold", "GOLD CURNCY:PX_LAST", "#ff8c00")

class LongTermCycleWTI(BaseLongTermCycleChart):
    def __init__(self): super().__init__("Long Term Cycles - WTI", "WTI:PX_LAST", "#ff00b8")