from ix.db.query import Series, Offset, Cycle, M2, financial_conditions_us as fci_us
from ix.dash.settings import theme
from ix.misc.date import twentyyearsbefore, today
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import ix
import os

# =========================
# Style Utilities (Dark Theme)
# =========================


def _px_from_rem(rem: str) -> int:
    """theme.space(n) -> "Xrem" 문자열을 px 정수로 변환"""
    return int(str(rem).replace("rem", "")) * 16


def apply_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=theme.bg,
        plot_bgcolor=theme.bg_light,
        font=dict(
            color=theme.text,
            family="SF Pro Display, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif",
            size=12,
        ),
        title=dict(
            text=f"<b>{title}</b>" if title else None,
            font=dict(size=20, color=theme.text),
            y=0.98,
            x=0.02,
            xanchor="left",
            yanchor="top",
        ),
        # legend=dict(
        #     orientation="h",
        #     yanchor="bottom",
        #     y=1.02,  # Keep legend position but ensure title is higher
        #     xanchor="left",
        #     x=0.02,
        #     bgcolor="rgba(0,0,0,0)",
        #     bordercolor=theme.border,
        #     borderwidth=0,
        #     font=dict(color=theme.text, size=11),
        #     itemsizing="trace",
        # ),
        legend=dict(
            x=0.01,
            y=0.99,
            bordercolor="gray",
            borderwidth=0,
            orientation="h",
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=theme.bg_light,
            bordercolor=theme.border,
            font=dict(color=theme.text, size=11),
        ),
        margin=dict(
            l=_px_from_rem(theme.space(16)),
            r=_px_from_rem(theme.space(12)),
            t=_px_from_rem(theme.space(24)),
            b=_px_from_rem(theme.space(8)),
        ),
        autosize=True,
    )
    # 공통 그리드/축 라인
    fig.update_xaxes(
        showgrid=True,
        gridcolor=theme.border,
        gridwidth=1,
        zeroline=False,
        showline=True,
        linecolor=theme.border,
        linewidth=1,
        tickfont=dict(color=theme.text_light, size=10),
        title_font=dict(color=theme.text_light, size=11),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=theme.border,
        gridwidth=1,
        zeroline=True,
        zerolinecolor=theme.text_light,
        zerolinewidth=1,
        showline=True,
        linecolor=theme.border,
        linewidth=1,
        tickfont=dict(color=theme.text_light, size=10),
        title_font=dict(color=theme.text_light, size=11),
    )
    return fig


def apply_axes(
    fig: go.Figure,
    y_title: str = "",
    y_tickformat: str | None = None,
    y_range: list[float] | None = None,
    y2_title: str | None = None,
    y2_tickformat: str | None = None,
    y2_range: list[float] | None = None,
    show_y2_grid: bool = False,
):
    fig.update_yaxes(
        title_text=f"<b>{y_title}</b>" if y_title else None,
        tickformat=y_tickformat,
        range=y_range,
    )
    if y2_title is not None:
        fig.update_layout(
            yaxis2=dict(
                title=dict(
                    text=f"<b>{y2_title}</b>",
                    font=dict(color=theme.text_light, size=11),
                ),
                overlaying="y",
                side="right",
                tickfont=dict(color=theme.text_light, size=10),
                showline=True,
                linecolor=theme.border,
                linewidth=1,
                showgrid=show_y2_grid,
                tickformat=y2_tickformat,
                range=y2_range,
            )
        )
    return fig


def theme_palette() -> list[str]:
    """Return a list of theme colors with safe fallbacks.
    Tries optional attributes (success, warning, danger, info, secondary, accent, muted)
    and falls back to a small default palette if missing. Ensures primary comes first.
    """
    prefer = [
        getattr(theme, name, None)
        for name in [
            "success",
            "warning",
            "danger",
            "info",
            "secondary",
            "accent",
            "muted",
        ]
    ]
    # keep only valid strings
    prefer = [c for c in prefer if isinstance(c, str) and len(c) > 0]
    # if nothing available, use a sane fallback set
    if not prefer:
        prefer = ["#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#22c55e", "#14b8a6"]
    # put primary at the front if not already
    palette = [theme.primary] + [
        c for c in prefer if c != getattr(theme, "primary", None)
    ]
    return palette


# =========================
# Charts
# =========================


def financial_conditions_us():
    fci = Offset(fci_us(), months=6)
    cyc = Cycle(fci, 60 * 5)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_fci = fci.values[-1] if len(fci.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=fci.index,
            y=fci.values,
            name=(
                f"FCI 6M Lead ({latest_fci:.2%})"
                if latest_fci is not None
                else "FCI 6M Lead"
            ),
            line=dict(color=theme.primary, width=3),
            hovertemplate="<b>FCI</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cyc.index,
            y=cyc.values,
            name=f"Cycle ({latest_cyc:.2%})" if latest_cyc is not None else "Cycle",
            line=dict(color=theme.success, width=3, dash="dot"),
            hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.1f})" if latest_ism is not None else "ISM PMI",
            yaxis="y2",
            line=dict(color=theme.warning, width=3),
            hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
        )
    )

    apply_layout(fig, "US Financial Conditions & Economic Indicators")
    apply_axes(
        fig,
        y_title="Financial Conditions Index (%)",
        y_tickformat=".0%",
        y_range=[-1, 1],
        y2_title="ISM PMI",
        y2_range=[30, 70],
        show_y2_grid=False,
    )

    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.text_light,
        line_width=1,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.text_light,
        yref="y2",
    )
    return fig


def global_liquidity_cycle():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    gl = Offset(M2("ME").WorldTotal.pct_change(12), months=6)
    gl = _normalize_percent(gl)
    cyc = Cycle(gl, 60)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_gl = gl.values[-1] if len(gl.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=gl.index,
            y=gl.values,
            name=(
                f"Global Liquidity 6M Lead ({latest_gl:.2%})"
                if latest_gl is not None
                else "Global Liquidity 6M Lead"
            ),
            line=dict(color=theme.primary, width=3),
            hovertemplate="<b>Global Liquidity YoY</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cyc.index,
            y=cyc.values,
            name=f"Cycle ({latest_cyc:.2%})" if latest_cyc is not None else "Cycle",
            line=dict(color=theme.warning, width=3, dash="dot"),
            hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.1f})" if latest_ism is not None else "ISM PMI",
            yaxis="y2",
            line=dict(color=theme.success, width=3),
            hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
        )
    )

    apply_layout(fig, "Global M2 Liquidity Cycle")
    apply_axes(
        fig,
        y_title="Global Liquidity YoY (%)",
        y_tickformat=".0%",
        y2_title="ISM PMI",
        y2_range=[30, 70],
        show_y2_grid=False,
    )
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.text_light,
        line_width=1,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.text_light,
        yref="y2",
    )
    return fig


def m2_country_contributions():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    start = twentyyearsbefore()
    end = today()

    m2 = M2("ME")
    total = _normalize_percent(m2.WorldTotal.pct_change(12).loc[start:end])
    contrib = {
        k: _normalize_percent(v.loc[start:end]) for k, v in m2.WorldContribution.items()
    }
    latest_total = total.iloc[-1] if len(total) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total.values,
            name=f"Total ({latest_total:.2%})" if latest_total is not None else "Total",
            mode="lines",
            line=dict(color=theme.primary, width=3),
            hovertemplate="<b>Total</b>: %{y:.2%}<extra></extra>",
        )
    )

    palette = theme_palette()
    for i, (name, s) in enumerate(contrib.items()):
        if s is None or len(s) == 0:
            continue
        fig.add_trace(
            go.Bar(
                x=s.index,
                y=s.values,
                name=name,
                marker_color=palette[i % len(palette)],
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )

    fig.update_layout(barmode="relative")
    apply_layout(fig, "M2 Country Contributions")
    apply_axes(fig, y_title="M2 Contribution (%)", y_tickformat=".0%")
    return fig


def m2_country_yoy():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    start = pd.Timestamp.today() - pd.DateOffset(years=20)
    end = today()

    m2q = ix.db.query.M2()
    world_df = m2q.World
    yoy = world_df.pct_change(12).loc[start:end].apply(_normalize_percent)

    fig = go.Figure()
    palette = theme_palette()

    for i, col in enumerate(yoy.columns):
        s = yoy[col].dropna()
        if s.empty:
            continue
        latest = s.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=f"{col} ({latest:.2%})",
                mode="lines",
                line=dict(color=palette[i % len(palette)], width=2),
                hovertemplate=f"<b>{col} YoY</b>: %{{y:.2%}}<extra></extra>",
            )
        )

    apply_layout(fig, "M2 YoY by Country")
    apply_axes(fig, y_title="M2 YoY (%)", y_tickformat=".1%")
    return fig


def ism_cycle_vs_asset(asset_name, asset_series, color_index=0):

    ism = Series("ISMPMI_M:PX_LAST")
    cycle = Cycle(ism, 48)

    performance_yoy = asset_series.resample("W-Fri").last().ffill().pct_change(52)

    latest_ism = ism.iloc[-1] if len(ism) > 0 else None
    latest_cycle = cycle.iloc[-1] if len(cycle) > 0 else None
    latest_performance = performance_yoy.iloc[-1] if len(performance_yoy) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.2f})" if latest_ism is not None else "ISM PMI",
            mode="lines",
            line=dict(color=theme.primary, width=3),
            yaxis="y1",
            hovertemplate="<b>ISM PMI</b>: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cycle.index,
            y=cycle.values,
            name=f"Cycle ({latest_cycle:.2f})" if latest_cycle is not None else "Cycle",
            mode="lines",
            line=dict(color=theme.warning, width=3, dash="dot"),
            yaxis="y1",
            hovertemplate="<b>Cycle</b>: %{y:.2f}<extra></extra>",
        )
    )

    palette = theme_palette()
    asset_color = palette[color_index % len(palette)]
    perf_name = f"{asset_name} YoY" + (
        f" ({latest_performance:.1%})" if latest_performance is not None else ""
    )

    fig.add_trace(
        go.Bar(
            x=performance_yoy.index,
            y=performance_yoy,
            name=perf_name,
            marker=dict(color=asset_color),
            opacity=0.6,
            yaxis="y2",
            hovertemplate=f"<b>{asset_name} YoY</b> : %{{y:.1%}}<extra></extra>",
        )
    )

    apply_layout(fig, f"ISM Cycle vs {asset_name}")
    apply_axes(
        fig,
        y_title="ISM PMI",
        y2_title=f"{asset_name} YoY (%)",
        y2_tickformat=".1%",
    )

    fig.add_hline(
        y=50,
        line_width=1,
        line_dash="dot",
        line_color=theme.text_light,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.text_light,
    )
    return fig


# Convenience wrappers (동일 다크 테마 자동 적용)


def ism_vs_sp500():
    sp500 = Series("SPX Index:PX_LAST")
    return ism_cycle_vs_asset("S&P 500", sp500, 0)


def ism_vs_treasury():
    treasury = Series("TRYUS10Y:PX_YTM")
    return ism_cycle_vs_asset("US Treasury 10Y", treasury, 1)


def ism_vs_oil():
    oil = Series("CL1 Comdty:PX_LAST")
    return ism_cycle_vs_asset("Crude Oil", oil, 2)


def ism_vs_bitcoin():
    bitcoin = Series("XBTUSD Curncy:PX_LAST")
    return ism_cycle_vs_asset("Bitcoin", bitcoin, 3)


def ism_vs_dollar():
    dollar = Series("DXY Index:PX_LAST")
    return ism_cycle_vs_asset("Dollar Index", dollar, 4)


def ism_vs_gold_copper_ratio():
    copper = Series("HG1 Comdty:PX_LAST")
    gold = Series("GC1 Comdty:PX_LAST")
    ratio = gold / copper
    return ism_cycle_vs_asset("Gold/Copper Ratio", ratio, 5)


from .fed_net_liquidity_sp500 import fed_net_liquidity_vs_sp500
from .utils import credit_impulse_us_vs_cn
from .utils import investor_positions
from .pim_mfg_regime import pmi_mfg_regime
from .pim_mfg_regime import oecd_cli_regime

# Registry
CHART_FUNCTIONS = {
    "financial_conditions_us": financial_conditions_us,
    "global_liquidity_cycle": global_liquidity_cycle,
    "m2_country_contributions": m2_country_contributions,
    "m2_country_yoy": m2_country_yoy,
    "ism_vs_sp500": ism_vs_sp500,
    "ism_vs_treasury": ism_vs_treasury,
    "ism_vs_oil": ism_vs_oil,
    "ism_vs_bitcoin": ism_vs_bitcoin,
    "ism_vs_dollar": ism_vs_dollar,
    "ism_vs_gold_copper_ratio": ism_vs_gold_copper_ratio,
    "fed_net_liquidity_vs_sp500": fed_net_liquidity_vs_sp500,
    "credit_impulse_us_vs_cn": credit_impulse_us_vs_cn,
    "investor_positions": investor_positions,
    "pmi_mfg_regime": pmi_mfg_regime,
    "oecd_cli_regime": oecd_cli_regime,
}


def get_chart_by_name(chart_name: str) -> go.Figure:
    if chart_name in CHART_FUNCTIONS:
        return CHART_FUNCTIONS[chart_name]()
    available = list(CHART_FUNCTIONS.keys())
    raise ValueError(f"Chart '{chart_name}' not found. Available charts: {available}")


def create_charts_safely() -> dict[str, go.Figure]:
    """Create all charts with error handling (공통 다크 테마 반영)."""
    results: dict[str, go.Figure] = {}
    for chart_name, chart_func in CHART_FUNCTIONS.items():
        try:
            fig = chart_func()
            if fig is not None:
                results[chart_name] = fig
        except Exception as e:
            print(f"✗ Error creating {chart_name}: {e}")
    print(f"\nSuccessfully created {len(results)} out of {len(CHART_FUNCTIONS)} charts")
    return results


def plot_all_charts(
    order: list[str] | None = None,
    renderer: str | None = None,
    show: bool = True,
    save_dir: str | None = None,
    filename_prefix: str = "",
    include_plotlyjs: str = "cdn",
    verbose: bool = True,
) -> dict[str, go.Figure]:
    """
    Create and (optionally) show/save all charts in a unified dark style.

    Parameters
    ----------
    order : list[str] | None
        표시/저장할 차트 이름 순서. None이면 CHART_FUNCTIONS 순서를 사용.
    renderer : str | None
        plotly 렌더러 지정(e.g., "browser", "notebook", "vscode").
    show : bool
        True면 각 차트를 .show()로 화면에 표시.
    save_dir : str | None
        경로 지정 시 각 차트를 독립 HTML로 저장. 디렉토리가 없으면 생성.
    filename_prefix : str
        저장 파일명 접두사(옵션). 예: "macro_"
    include_plotlyjs : str
        write_html의 include_plotlyjs 옵션("cdn" 권장).
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    dict[str, go.Figure]
        {차트이름: Figure} 매핑
    """
    if renderer:
        pio.renderers.default = renderer

    # 1) 안전 생성
    figures = create_charts_safely()

    # 2) 순서 정리
    keys = order if order else list(CHART_FUNCTIONS.keys())
    keys = [k for k in keys if k in figures]  # 존재하는 키만

    # 3) 저장 경로 준비
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    # 4) 표시/저장
    for k in keys:
        fig = figures[k]

        if show:
            if verbose:
                print(f"Showing: {k}")
            fig.show()

        if save_dir:
            file_path = os.path.join(save_dir, f"{filename_prefix}{k}.html")
            if verbose:
                print(f"Saving: {file_path}")
            fig.write_html(file_path, include_plotlyjs=include_plotlyjs, full_html=True)

    if verbose:
        print(
            f"Rendered {len(keys)} charts. Renderer={pio.renderers.default}. Saved to: {save_dir or 'N/A'}"
        )

    return {k: figures[k] for k in keys}
