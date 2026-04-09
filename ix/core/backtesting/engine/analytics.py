"""StrategyAnalytics mixin — performance metrics, plotting, and attribution.

Mixed into ``Strategy`` via multiple inheritance so that
``strat.stats()``, ``strat.plot()``, etc. work on any strategy instance.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ix.common.performance.metrics import (
    to_ann_return,
    to_ann_volatility,
    aggregate_returns,
    drawdown_details,
    rolling_sharpe,
    roll_alpha,
    roll_sortino,
    roll_max_drawdown,
    roll_cagr,
    cumulative_contribution,
)


class StrategyAnalytics:
    """Mixin providing performance analytics, charting, and attribution.

    Expects the host class to expose:
    - ``self.nav`` — pd.Series of portfolio values
    - ``self.benchmark`` — pd.Series of benchmark values
    - ``self.dates`` — pd.DatetimeIndex
    - ``self.book`` — dict with backtest history
    - ``self.weights_history`` — pd.DataFrame of asset weights
    - ``self.universe`` — dict of universe config
    - ``self.pxs`` — pd.DataFrame of prices
    - ``self.code_to_name`` — dict mapping codes to names
    """

    # ------------------------------------------------------------------
    # Core metrics
    # ------------------------------------------------------------------

    def calculate_metrics(self, series: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics for a NAV series."""
        if series.empty or len(series) < 2:
            return {
                "Total Return": 0.0, "CAGR": 0.0, "Volatility": 0.0,
                "Sharpe": 0.0, "Sortino": 0.0, "Max Drawdown": 0.0,
                "Win Rate": 0.0, "Avg Daily Return": 0.0,
            }
        daily_ret = series.pct_change().dropna()
        total_return = (series.iloc[-1] / series.iloc[0]) - 1
        ann_ret = to_ann_return(series)
        ann_vol = to_ann_volatility(series)
        sharpe = (ann_ret / ann_vol) if ann_vol != 0 else 0
        sortino = self._calculate_sortino(daily_ret)
        max_dd = ((series - series.cummax()) / series.cummax()).min()
        win_rate = (daily_ret > 0).sum() / len(daily_ret) if len(daily_ret) > 0 else 0

        return {
            "Total Return": total_return,
            "CAGR": ann_ret,
            "Volatility": ann_vol,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Max Drawdown": max_dd,
            "Win Rate": win_rate,
            "Avg Daily Return": daily_ret.mean(),
        }

    @staticmethod
    def _calculate_sortino(returns: pd.Series, mar: float = 0.0) -> float:
        """Calculate Sortino ratio."""
        excess = returns - mar / 252
        downside = excess[excess < 0].std()
        if downside == 0 or pd.isna(downside):
            return 0.0
        return (excess.mean() * 252) / (downside * np.sqrt(252))

    # ------------------------------------------------------------------
    # Stats table
    # ------------------------------------------------------------------

    def stats(self) -> pd.DataFrame:
        """Generate performance statistics table.

        Uses stored ``_loaded_performance`` if strategy was loaded from DB.
        """
        perf = getattr(self, "_loaded_performance", None)
        if perf is not None:
            bm = perf.get("benchmark", {})
            formatted = {
                "Strategy": {
                    "Total Return": f"{perf.get('total_return', 0):.2%}",
                    "CAGR": f"{perf.get('cagr', 0):.2%}",
                    "Volatility": f"{perf.get('vol', 0):.2%}",
                    "Sharpe": f"{perf.get('sharpe', 0):.2f}",
                    "Sortino": f"{perf.get('sortino', 0):.2f}",
                    "Max DD": f"{perf.get('max_dd', 0):.2%}",
                    "Win Rate": f"{perf.get('win_rate', 0):.2%}",
                    "Alpha": f"{perf.get('alpha', 0):.2%}",
                    "IR": f"{perf.get('ir', 0):.2f}",
                },
                "Benchmark": {
                    "Total Return": f"{bm.get('total_return', 0):.2%}",
                    "CAGR": f"{bm.get('cagr', 0):.2%}",
                    "Volatility": f"{bm.get('vol', 0):.2%}",
                    "Sharpe": f"{bm.get('sharpe', 0):.2f}",
                    "Sortino": f"{bm.get('sortino', 0):.2f}",
                    "Max DD": f"{bm.get('max_dd', 0):.2%}",
                },
            }
            return pd.DataFrame(formatted)

        strategy_metrics = self.calculate_metrics(self.nav)
        benchmark_metrics = self.calculate_metrics(self.benchmark)

        formatted = {}
        for name, metrics in {"Strategy": strategy_metrics, "Benchmark": benchmark_metrics}.items():
            formatted[name] = {
                "Total Return": f"{metrics['Total Return']:.2%}",
                "CAGR": f"{metrics['CAGR']:.2%}",
                "Volatility": f"{metrics['Volatility']:.2%}",
                "Sharpe": f"{metrics['Sharpe']:.2f}",
                "Sortino": f"{metrics['Sortino']:.2f}",
                "Max DD": f"{metrics['Max Drawdown']:.2%}",
                "Win Rate": f"{metrics['Win Rate']:.2%}",
            }

        total_costs = sum(self.book["transaction_costs"])
        turnovers = [t for t in self.book["turnover"] if t > 0]
        avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0
        formatted["Strategy"]["Avg Turnover"] = f"{avg_turnover:.2%}"
        formatted["Strategy"]["Total Costs"] = f"${total_costs:,.0f}"

        return pd.DataFrame(formatted)

    # ------------------------------------------------------------------
    # Tearsheet plot
    # ------------------------------------------------------------------

    def plot(self):
        """Generate comprehensive tearsheet with 4 panels."""
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.06,
            row_heights=[0.40, 0.20, 0.25, 0.15],
            subplot_titles=("Cumulative Performance", "Drawdown", "Asset Allocation", "Rolling Sharpe (6M)"),
        )

        # 1. NAV
        fig.add_trace(go.Scatter(x=self.dates, y=self.nav, name="Strategy", line=dict(color="#2E86AB", width=2.5), legendgroup="main"), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.dates, y=self.benchmark, name="Benchmark", line=dict(color="#A23B72", dash="dot", width=2), legendgroup="main"), row=1, col=1)

        # 2. Drawdown
        dd = (self.nav / self.nav.cummax()) - 1
        dd_bm = (self.benchmark / self.benchmark.cummax()) - 1
        fig.add_trace(go.Scatter(x=self.dates, y=dd, name="Strategy DD", fill="tozeroy", line=dict(color="#C73E1D", width=0), fillcolor="rgba(199, 62, 29, 0.5)", legendgroup="dd"), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.dates, y=dd_bm, name="Benchmark DD", line=dict(color="#A23B72", width=1, dash="dot"), legendgroup="dd"), row=2, col=1)

        # 3. Allocations
        weights_df = self.weights_history
        if not weights_df.empty:
            colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
            avg_weights = weights_df.mean().sort_values(ascending=False)
            for i, col in enumerate(avg_weights.index):
                fig.add_trace(go.Scatter(x=weights_df.index, y=weights_df[col], name=col, stackgroup="allocation", mode="none", fillcolor=colors[i % len(colors)], legendgroup="allocation"), row=3, col=1)

        # 4. Rolling Sharpe
        returns = self.nav.pct_change()
        rs = (returns.rolling(126).mean() / returns.rolling(126).std()) * np.sqrt(252)
        fig.add_trace(go.Scatter(x=self.dates, y=rs, name="Rolling Sharpe", line=dict(color="#18A558", width=2), showlegend=False), row=4, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=4, col=1, line_width=1)
        fig.add_hline(y=1, line_dash="dash", line_color="lightgray", row=4, col=1, line_width=0.5)

        fig.update_layout(height=1200, title_text=f"{self.__class__.__name__} Performance Tearsheet", hovermode="x unified", template="plotly_white", legend=dict(groupclick="toggleitem", tracegroupgap=180))
        fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
        fig.update_yaxes(title_text="Weight", tickformat=".0%", row=3, col=1, range=[0, 1])
        fig.update_yaxes(title_text="Sharpe Ratio", row=4, col=1)
        fig.update_xaxes(title_text="Date", row=4, col=1)
        return fig

    # ------------------------------------------------------------------
    # Calendar returns, drawdowns, rolling metrics, attribution
    # ------------------------------------------------------------------

    def calendar_returns(self) -> pd.DataFrame:
        """Monthly returns table with annual totals."""
        daily_ret = self.nav.pct_change().dropna()
        if daily_ret.empty:
            return pd.DataFrame()
        monthly = aggregate_returns(daily_ret, convert_to="monthly")
        monthly.index = pd.DatetimeIndex(monthly.index)
        table = pd.DataFrame({"Year": monthly.index.year, "Month": monthly.index.month, "Return": monthly.values})
        grid = table.pivot(index="Year", columns="Month", values="Return")
        grid.columns = [["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1] for m in grid.columns]
        annual = aggregate_returns(daily_ret, convert_to="yearly")
        annual.index = pd.DatetimeIndex(annual.index)
        grid["Year"] = pd.Series(annual.values, index=annual.index.year)
        return grid

    def drawdown_table(self, top_n: int = 5) -> pd.DataFrame:
        """Top N worst drawdown episodes."""
        daily_ret = self.nav.pct_change().dropna()
        if daily_ret.empty:
            return pd.DataFrame()
        details = drawdown_details(daily_ret)
        if details.empty:
            return details
        return details.head(top_n).reset_index(drop=True)

    def rolling_metrics(self, window: int = 252) -> pd.DataFrame:
        """Rolling Sharpe, Alpha, Sortino, Max DD, CAGR."""
        strat_ret = self.nav.pct_change().dropna()
        bench_ret = self.benchmark.pct_change().dropna()
        if strat_ret.empty:
            return pd.DataFrame()
        result = pd.DataFrame({
            "Sharpe": rolling_sharpe(strat_ret, window=window),
            "Alpha": roll_alpha(strat_ret, bench_ret, window=window),
            "Sortino": roll_sortino(strat_ret, window=window),
            "Max DD": roll_max_drawdown(strat_ret, window=window),
            "CAGR": roll_cagr(strat_ret, window=window),
        })
        return result.dropna(how="all")

    def attribution(self) -> Dict[str, Any]:
        """Per-asset return contribution and Brinson-Fachler decomposition."""
        weights_df = self.weights_history
        if weights_df.empty or self.pxs.empty:
            return {"contribution": pd.DataFrame(), "brinson": None}

        asset_ret = self.pxs.pct_change().rename(columns=self.code_to_name)
        common_dates = weights_df.index.intersection(asset_ret.index)
        common_assets = weights_df.columns.intersection(asset_ret.columns)
        if common_dates.empty or common_assets.empty:
            return {"contribution": pd.DataFrame(), "brinson": None}

        w = weights_df.reindex(index=common_dates, columns=common_assets).fillna(0.0)
        r = asset_ret.reindex(index=common_dates, columns=common_assets).fillna(0.0)
        contrib = cumulative_contribution(r, w)

        brinson_result = None
        try:
            from ix.common.performance.attribution import brinson_fachler, brinson_fachler_summary
            bm_weights_raw = pd.Series({name: v["weight"] for name, v in self.universe.items()})
            bm_w = pd.DataFrame([bm_weights_raw] * len(common_dates), index=common_dates, columns=bm_weights_raw.index).reindex(columns=common_assets, fill_value=0.0)
            bf = brinson_fachler(portfolio_weights=w, benchmark_weights=bm_w, portfolio_returns=r, benchmark_returns=r)
            brinson_result = brinson_fachler_summary(bf)
        except Exception:
            pass

        return {"contribution": contrib, "brinson": brinson_result}
