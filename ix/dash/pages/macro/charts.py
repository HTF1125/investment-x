import pandas as pd
import plotly.graph_objects as go
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from dateutil.relativedelta import relativedelta

# Import your existing modules
import ix
from ix import MonthEndOffset, Cycle, Series, M2, financial_conditions_us
from ix.misc.date import twentyyearsbefore, today
from ix.dash.settings import theme


class BasePlot(ABC):
    """Base class for all financial charts"""

    def __init__(self, title: str = "", chart_id: str = ""):
        self.title = title
        self.chart_id = chart_id
        self.theme = theme
        self._data = None
        self._x_range = None

    @abstractmethod
    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> Any:
        """Load and prepare data for the chart"""
        pass

    @abstractmethod
    def _create_traces(self, fig: go.Figure) -> go.Figure:
        """Add traces to the figure"""
        pass

    def _apply_base_layout(
        self, fig: go.Figure, x_range: Optional[List] = None
    ) -> go.Figure:
        """Apply common dark theme layout to figure"""
        fig.update_layout(
            title="",  # No title in the plot itself
            font=dict(color=self.theme.text),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.01,
                font=dict(color=self.theme.text),
                bgcolor="rgba(255,255,255,0.05)",
            ),
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor=self.theme.bg,
            plot_bgcolor=self.theme.bg,
            hovermode="x unified",
            hoverlabel=dict(bgcolor=self.theme.bg_light, font_color=self.theme.text),
            transition=dict(duration=400, easing="cubic-in-out"),
        )

        if x_range is not None:
            fig.update_xaxes(range=x_range)

        fig.update_xaxes(
            showgrid=False,
            tickformat="%y.%m",
            tickfont=dict(color=self.theme.text_light),
            mirror=True,
            showline=True,
            linecolor=self.theme.border,
            rangeslider=dict(visible=False),
            rangeselector=dict(visible=False),
        )

        return fig

    def _setup_left_axis(
        self, fig: go.Figure, tickformat: Optional[str] = None
    ) -> go.Figure:
        """Configure left y-axis"""
        fig.update_layout(
            yaxis=dict(
                gridcolor=self.theme.border,
                zeroline=False,
                mirror=True,
                showline=True,
                linecolor=self.theme.border,
                tickfont=dict(color=self.theme.text_light),
                title=None,
                tickformat=tickformat,
            )
        )
        return fig

    def _setup_right_axis(
        self,
        fig: go.Figure,
        range_: Optional[List] = None,
        tickformat: Optional[str] = None,
    ) -> go.Figure:
        """Configure right y-axis"""
        fig.update_layout(
            yaxis2=dict(
                overlaying="y",
                side="right",
                range=range_,
                showgrid=False,
                zeroline=False,
                mirror=True,
                showline=True,
                linecolor=self.theme.border,
                tickfont=dict(color=self.theme.text_light),
                title=None,
                tickformat=tickformat,
            )
        )
        return fig

    def _normalize_percent(self, s: pd.Series) -> pd.Series:
        """Ensure percent-like series are in decimal form"""
        s = s.astype(float)
        if s.dropna().abs().median() > 1.5:
            return s / 100.0
        return s

    def plot(
        self,
        x_range: Optional[List] = None,
    ) -> go.Figure:
        """Main method to create the plot"""
        # Load data
        self._data = self._load_data()

        # Set x_range - handle special case for M2ContributionPlot
        if x_range is None:
            if isinstance(self._data, tuple):
                # For M2ContributionPlot which returns (total, contrib)
                total, contrib = self._data
                if not total.empty:
                    self._x_range = [
                        total.index.min(),
                        total.index.max() + pd.DateOffset(months=4),
                    ]
                else:
                    self._x_range = None
            elif hasattr(self._data, "index") and not self._data.empty:
                self._x_range = [
                    self._data.index.min(),
                    self._data.index.max() + pd.DateOffset(months=4),
                ]
            else:
                self._x_range = None
        else:
            self._x_range = x_range

        # Create figure and add traces
        fig = go.Figure()
        fig = self._create_traces(fig)

        # Apply base styling
        fig = self._apply_base_layout(fig, self._x_range)

        return fig


class FCIPlot(BasePlot):
    """Financial Conditions Index chart"""

    def __init__(self):
        super().__init__("Financial Conditions & Business Cycles", "main")

    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:

        fci_me = financial_conditions_us().resample("ME").last()
        fci6 = MonthEndOffset(fci_me, 6).mul(100)
        cyc = Cycle(fci6, 60)
        ism = Series("ISMPMI_M:PX_LAST", freq="ME")

        df = pd.DataFrame({"FCI (6M Lead)": fci6, "Cycle": cyc, "ISM PMI Mfg (R)": ism})

        return df.dropna(how="all").resample("ME").last().dropna()

    def _create_traces(self, fig: go.Figure) -> go.Figure:
        # Left axis traces
        for col, color_name in [("FCI (6M Lead)", "blue"), ("Cycle", "green")]:
            if col not in self._data.columns:
                continue
            latest = self._data[col].iloc[-1]
            name = f"{col} ({latest:.1f})"

            fig.add_trace(
                go.Scatter(
                    x=self._data.index,
                    y=self._data[col],
                    mode="lines",
                    name=name,
                    line=dict(
                        width=3, shape="spline", color=self.theme.color(color_name)
                    ),
                    hovertemplate=f"<b>{col}</b><br>%{{x|%Y-%m}}: %{{y:.1f}}<extra></extra>",
                )
            )

        # Right axis: ISM
        if "ISM PMI Mfg (R)" in self._data.columns:
            latest_ism = self._data["ISM PMI Mfg (R)"].iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=self._data.index,
                    y=self._data["ISM PMI Mfg (R)"],
                    mode="lines",
                    name=f"ISM PMI Mfg (R) ({latest_ism:.2f})",
                    line=dict(width=3, shape="spline", color=self.theme.cyan()),
                    yaxis="y2",
                    hovertemplate="<b>ISM PMI Mfg (R)</b><br>%{x|%Y-%m}: %{y:.2f}<extra></extra>",
                )
            )

        # Add reference line at 50
        fig.add_hline(y=50, line_width=1, line_dash="dot", line_color="#94a3b8")

        # Setup axes
        fig = self._setup_left_axis(fig)
        fig = self._setup_right_axis(fig, range_=[30, 70])

        return fig


class LiquidityPlot(BasePlot):
    """Global M2 Liquidity Cycle chart"""

    def __init__(self):
        super().__init__("Global M2 Liquidity Cycle", "liq")

    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:

        gl = MonthEndOffset(M2("ME").WorldTotal.pct_change(12), months=6)
        gl = self._normalize_percent(gl)
        cy = Cycle(gl, 60)
        ism = Series("ISMPMI_M:PX_LAST", freq="ME")

        df = pd.DataFrame(
            {"Global Liquidity YoY (6M Lead)": gl, "Cycle": cy, "ISM PMI Mfg (R)": ism}
        )

        return df.dropna(how="all").resample("ME").last().dropna()

    def _create_traces(self, fig: go.Figure) -> go.Figure:
        # Left axis traces
        for col, color_name in [
            ("Global Liquidity YoY (6M Lead)", "blue"),
            ("Cycle", "yellow"),
        ]:
            if col not in self._data.columns:
                continue
            latest = self._data[col].iloc[-1]
            name = f"{col} ({latest:.2%})"

            fig.add_trace(
                go.Scatter(
                    x=self._data.index,
                    y=self._data[col],
                    mode="lines",
                    name=name,
                    line=dict(
                        width=3, shape="spline", color=self.theme.color(color_name)
                    ),
                    hovertemplate=f"<b>{col}</b><br>%{{x|%Y-%m}}: %{{y:.2%}}<extra></extra>",
                )
            )

        # Right axis: ISM
        if "ISM PMI Mfg (R)" in self._data.columns:
            latest_ism = self._data["ISM PMI Mfg (R)"].iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=self._data.index,
                    y=self._data["ISM PMI Mfg (R)"],
                    mode="lines",
                    name=f"ISM PMI Mfg (R) ({latest_ism:.2f})",
                    line=dict(width=3, shape="spline", color=self.theme.green()),
                    yaxis="y2",
                    hovertemplate="<b>ISM PMI Mfg (R)</b><br>%{x|%Y-%m}: %{y:.2f}<extra></extra>",
                )
            )

        # Add reference line at 50 on right axis
        fig.add_shape(
            type="line",
            xref="x",
            yref="y2",
            x0=self._data.index.min(),
            x1=self._data.index.max(),
            y0=50,
            y1=50,
            line=dict(width=1, dash="dot", color="#94a3b8"),
        )

        # Setup axes
        fig = self._setup_left_axis(fig, tickformat=".0%")
        fig = self._setup_right_axis(fig, range_=[30, 70])

        return fig


class M2ContributionPlot(BasePlot):
    """M2 Country Contributions chart"""

    def __init__(self):
        super().__init__("M2 Country Contributions", "m2c")

    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> Tuple[pd.Series, Dict]:
        start = twentyyearsbefore() if start is None else pd.Timestamp(start)
        end = today() if end is None else pd.Timestamp(end)

        m2 = M2("ME")
        total = self._normalize_percent(m2.WorldTotal.pct_change(12).loc[start:end])
        contrib = {
            k: self._normalize_percent(v.loc[start:end])
            for k, v in m2.WorldContribution.items()
        }

        return total, contrib

    def _create_traces(self, fig: go.Figure) -> go.Figure:
        total, contrib = self._data

        # Total line
        latest_total = total.dropna().iloc[-1] if not total.empty else None
        fig.add_trace(
            go.Scatter(
                x=total.index,
                y=total.values,
                name=(
                    f"Total ({latest_total:.2%})"
                    if latest_total is not None
                    else "Total"
                ),
                mode="lines",
                line=dict(color=self.theme.blue(), width=3),
                hovertemplate="<b>Total</b>: %{y:.2%}<extra></extra>",
            )
        )

        # Contribution bars - use theme chart colors
        chart_colors = self.theme.chart_colors
        for i, (name, s) in enumerate(contrib.items()):
            fig.add_trace(
                go.Bar(
                    x=s.index,
                    y=s.values,
                    name=name,
                    marker_color=chart_colors[i % len(chart_colors)],
                    hovertemplate=f"<b>{name}</b>: " + "%{y:.2%}<extra></extra>",
                )
            )

        fig.update_layout(barmode="relative")

        # Setup axes
        fig = self._setup_left_axis(fig, tickformat=".0%")

        return fig


class M2CountryPlot(BasePlot):
    """M2 YoY by Country chart"""

    def __init__(self):
        super().__init__("M2 YoY by Country", "m2y")

    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:
        start = (
            (pd.Timestamp.today() - pd.DateOffset(years=20))
            if start is None
            else pd.Timestamp(start)
        )
        end = today() if end is None else pd.Timestamp(end)

        m2q = ix.db.query.M2()
        world_df = m2q.World
        yoy = world_df.pct_change(12).loc[start:end]

        # Normalize each column
        yoy = yoy.apply(self._normalize_percent)

        return yoy

    def _create_traces(self, fig: go.Figure) -> go.Figure:
        chart_colors = self.theme.chart_colors

        for i, col in enumerate(self._data.columns):
            s = self._data[col].dropna()
            if s.empty:
                continue

            latest = s.iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=s.index,
                    y=s.values,
                    name=f"{col} ({latest:.2%})",
                    mode="lines",
                    line=dict(color=chart_colors[i % len(chart_colors)], width=2),
                    hovertemplate=f"<b>{col} YoY</b>: " + "%{y:.2%}<extra></extra>",
                )
            )

        # Setup axes
        fig = self._setup_left_axis(fig, tickformat=".1%")

        return fig


class ISMCyclePlot(BasePlot):
    """ISM Business Cycle Analysis chart"""

    def __init__(self, asset_name: str, asset_series: Any, color_index: int = 0):
        super().__init__(
            f"ISM Cycle vs {asset_name}",
            f"ism_{asset_name.lower().replace(' ', '_').replace('&', 'and')}",
        )
        self.asset_name = asset_name
        self.asset_series = asset_series
        self.color_index = color_index

    def _load_data(
        self, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp] = None
    ) -> Dict[str, pd.Series]:
        start = (
            pd.Timestamp.today() - pd.DateOffset(years=20)
            if start is None
            else pd.Timestamp(start)
        )
        end = today() if end is None else pd.Timestamp(end)

        # Get ISM data
        ism = Series("ISMPMI_M:PX_LAST")
        cycle = Cycle(ism, 48)
        ism = ism.loc[start:end]
        cycle = cycle.loc[start:end]

        # Prepare asset performance YoY
        performance_yoy = (
            self.asset_series.resample("W-Fri").last().ffill().pct_change(52)
        )
        performance_yoy = performance_yoy[
            (performance_yoy.index >= start) & (performance_yoy.index <= end)
        ]

        return {"ism": ism, "cycle": cycle, "performance": performance_yoy}

    def _create_traces(self, fig: go.Figure) -> go.Figure:
        ism = self._data["ism"]
        cycle = self._data["cycle"]
        performance = self._data["performance"]

        # ISM PMI
        latest_ism = ism.iloc[-1] if not ism.empty else None
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=(
                    f"ISM PMI ({latest_ism:.2f})"
                    if latest_ism is not None
                    else "ISM PMI"
                ),
                mode="lines",
                line=dict(color=self.theme.blue(), width=3, shape="spline"),
                yaxis="y1",
                hovertemplate="<b>ISM PMI</b> : %{y:.2f}<extra></extra>",
            )
        )

        # ISM Cycle
        latest_cycle = cycle.iloc[-1] if not cycle.empty else None
        fig.add_trace(
            go.Scatter(
                x=cycle.index,
                y=cycle.values,
                name="Cycle",
                mode="lines",
                line=dict(
                    color=self.theme.yellow(), width=3, shape="spline", dash="dot"
                ),
                yaxis="y1",
                hovertemplate="<b>Cycle: %{y:.2f}<extra></extra>",
            )
        )

        # Asset YoY %
        latest_performance = performance.iloc[-1] if not performance.empty else None
        asset_color = self.theme.chart_colors[
            self.color_index % len(self.theme.chart_colors)
        ]

        performance_name = f"{self.asset_name} YoY"
        if latest_performance is not None:
            performance_name += f" ({latest_performance:.1%})"

        fig.add_trace(
            go.Bar(
                x=performance.index,
                y=performance,
                name=performance_name,
                marker=dict(color=asset_color),
                opacity=0.6,
                yaxis="y2",
                hovertemplate=f"<b>{self.asset_name} YoY</b><br>%{{x|%Y-%m}}: %{{y:.1%}}<extra></extra>",
            )
        )

        # Add reference line at 50 for ISM
        fig.add_hline(y=50, line_width=1, line_dash="dot", line_color="#94a3b8")

        # Setup axes
        fig = self._setup_left_axis(fig)
        fig = self._setup_right_axis(fig, tickformat=".1%")

        return fig


def create_ism_chart_instances():
    """Create ISM chart instances for different assets"""
    from ix import Series

    assets = {
        "S&P500": Series("SPX Index:PX_LAST"),
        "US Treasury 10Y": Series("TRYUS10Y:PX_YTM"),
        "Crude Oil": Series("CL1 Comdty:PX_LAST"),
        "Bitcoin": Series("XBTUSD Curncy:PX_LAST"),
        "Dollar": Series("DXY Index:PX_LAST"),
        "Gold/Copper": Series("HG1 Comdty:PX_LAST") / Series("GC1 Comdty:PX_LAST"),
    }

    ism_charts = []
    for i, (name, data) in enumerate(assets.items()):
        try:
            ism_charts.append(ISMCyclePlot(name, data, i))
        except Exception as e:
            print(f"Error creating ISM chart for {name}: {e}")
            continue

    return ism_charts


# Chart registry for easy looping
CHART_CLASSES = [FCIPlot, LiquidityPlot, M2ContributionPlot, M2CountryPlot]
ISM_CHART_CLASSES = [ISMCyclePlot]


def create_all_chart_instances():
    """Create instances of all chart classes"""
    return [chart_class() for chart_class in CHART_CLASSES]


def get_chart_layout_data():
    """Get layout data for all charts - for use in Dash app"""
    chart_instances = create_all_chart_instances()

    layout_data = []
    for chart in chart_instances:
        layout_data.append(
            {"title": chart.title, "chart_id": chart.chart_id, "instance": chart}
        )

    return layout_data


# Example Dash integration functions
def build_initial_figures(init_x_range):
    """Build initial figures for all charts with given x_range"""
    figures = {}
    chart_instances = create_all_chart_instances()

    for chart in chart_instances:
        try:
            # Use the chart's own plot method with the x_range
            figures[chart.chart_id] = chart.plot(x_range=init_x_range)
        except Exception as e:
            print(f"Error creating {chart.chart_id} plot: {e}")
            continue

    return figures


# Data loading functions (matching original code structure)
def build_fci_df(start=None, end=None):
    """Build FCI dataframe - matches original function"""
    start = pd.Timestamp("2000-01-01") if start is None else pd.Timestamp(start)
    end = today() if end is None else pd.Timestamp(end)
    fci_me = FCIUS().resample("ME").last()
    fci6 = MonthEndOffset(fci_me, 6).mul(100)
    cyc = Cycle(fci6, 60)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    df = pd.DataFrame({"FCI (6M Lead)": fci6, "Cycle": cyc, "ISM PMI Mfg (R)": ism})
    return df.loc[start:end].dropna(how="all").resample("ME").last().dropna()


def build_liq_df(start=None, end=None):
    """Build liquidity dataframe - matches original function"""
    start = twentyyearsbefore() if start is None else pd.Timestamp(start)
    end = today() if end is None else pd.Timestamp(end)
    gl = MonthEndOffset(M2("ME").WorldTotal.pct_change(12), months=6)
    gl = _normalize_percent(gl)
    cy = Cycle(gl, 60)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")
    df = pd.DataFrame(
        {"Global Liquidity YoY (6M Lead)": gl, "Cycle": cy, "ISM PMI Mfg (R)": ism}
    )
    return df.loc[start:end].dropna(how="all").resample("ME").last().dropna()


def build_m2_total_contrib(start=None, end=None):
    """Build M2 contribution data - matches original function"""
    start = twentyyearsbefore() if start is None else pd.Timestamp(start)
    end = today() if end is None else pd.Timestamp(end)
    m2 = M2("ME")
    total = _normalize_percent(m2.WorldTotal.pct_change(12).loc[start:end])
    contrib = {
        k: _normalize_percent(v.loc[start:end]) for k, v in m2.WorldContribution.items()
    }
    return total, contrib


def build_m2_world_yoy(start=None, end=None):
    """Build M2 world YoY data - matches original function"""
    start = (
        (pd.Timestamp.today() - pd.DateOffset(years=20))
        if start is None
        else pd.Timestamp(start)
    )
    end = today() if end is None else pd.Timestamp(end)
    m2q = ix.db.query.M2()
    world_df = m2q.World
    yoy = world_df.pct_change(12).loc[start:end]
    yoy = yoy.apply(_normalize_percent)
    return yoy


def _normalize_percent(s: pd.Series) -> pd.Series:
    """Ensure percent-like series are in decimal form"""
    s = s.astype(float)
    if s.dropna().abs().median() > 1.5:
        return s / 100.0
    return s


# Create and display the 4 charts
def create_and_show_all_charts():
    """Create all 4 charts and return the figures"""

    # Create chart instances
    charts = create_all_chart_instances()
    figures = {}

    print("Creating 4 financial charts...")

    for chart in charts:
        try:
            print(f"Creating {chart.title} (ID: {chart.chart_id})...")

            # Create the plot
            fig = chart.plot()
            figures[chart.chart_id] = fig

            # Debug information
            print(f"  - Created figure with {len(fig.data)} traces")
            if hasattr(chart, "_data"):
                if isinstance(chart._data, tuple):
                    total, contrib = chart._data
                    print(
                        f"  - Data: Total series with {len(total)} points, {len(contrib)} contribution series"
                    )
                elif hasattr(chart._data, "shape"):
                    print(f"  - Data shape: {chart._data.shape}")
                else:
                    print(f"  - Data type: {type(chart._data)}")

            # Show the plot
            fig.show()

            print(f"✓ {chart.title} created successfully")

        except Exception as e:
            print(f"✗ Error creating {chart.title}: {e}")
            import traceback

            traceback.print_exc()
            continue

    return figures


# Usage example
if __name__ == "__main__":
    # Create and display all 4 charts
    all_figures = create_and_show_all_charts()

    print(f"\nSummary: Created {len(all_figures)} charts:")
    for chart_id, fig in all_figures.items():
        print(f"- {chart_id}: {len(fig.data)} traces")

    # Also demonstrate the chart data structure
    print("\nChart structure for Dash integration:")
    charts_data = get_chart_layout_data()
    for chart_data in charts_data:
        print(f"- {chart_data['title']} (ID: {chart_data['chart_id']})")


# Direct plotting function for immediate use
def plot_all_charts():
    """Simple function to create and show all charts immediately"""
    create_and_show_all_charts()


# Run the plots
