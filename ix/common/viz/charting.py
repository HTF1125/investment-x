"""Chart rendering, code execution, and export utilities.

Pure computation module — no FastAPI dependencies. Extracted from the
custom charts router to allow reuse by chart_packs, scripts, and tests.
"""
from __future__ import annotations

import base64
import concurrent.futures
import html
import json
import re
import traceback
from datetime import datetime
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from ix.common import get_logger
from ix.common.viz.theme import chart_theme
from ix.common.security.safe_custom_code import (
    SAFE_CUSTOM_CHART_BUILTINS,
    UnsafeCustomChartCodeError,
    validate_custom_chart_code,
)

logger = get_logger(__name__)

try:
    import orjson as _orjson
except ImportError:
    _orjson = None

try:
    from xhtml2pdf import pisa as _pisa
except ImportError:
    _pisa = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LEGACY_STYLE_PALETTE = [
    "#38bdf8",
    "#a855f7",
    "#f472b6",
    "#10b981",
    "#fbbf24",
    "#6366f1",
    "#f43f5e",
    "#2dd4bf",
    "#f97316",
]

_SCOPE_IMPORT_RE = re.compile(
    r"^(?P<indent>\s*)(?:from\s+(?:ix|ix\.\w+(?:\.\w+)*|plotly|plotly\.\w+|datetime|typing)\s+import\s+[^\n]+|import\s+(?:numpy|pandas|plotly|datetime|time)(?:\.\w+)*(?:\s+as\s+\w+)?)\s*$",
    flags=re.MULTILINE,
)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def json_dumps_fast(payload: Any) -> str:
    """Fast JSON serialization, preferring orjson when available."""
    if _orjson is not None:
        return _orjson.dumps(payload).decode("utf-8")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Legacy chart helpers (injected into custom-code exec scope)
# ---------------------------------------------------------------------------

def legacy_get_color(name: str, index: int = 0) -> str:
    fixed = {
        "America": _LEGACY_STYLE_PALETTE[0],
        "US": _LEGACY_STYLE_PALETTE[0],
        "Primary": _LEGACY_STYLE_PALETTE[0],
        "S&P 500": _LEGACY_STYLE_PALETTE[0],
        "SPY": _LEGACY_STYLE_PALETTE[0],
        "Europe": _LEGACY_STYLE_PALETTE[1],
        "EU": _LEGACY_STYLE_PALETTE[1],
        "Japan": _LEGACY_STYLE_PALETTE[2],
        "JP": _LEGACY_STYLE_PALETTE[2],
        "Apac": _LEGACY_STYLE_PALETTE[3],
        "Emerald": _LEGACY_STYLE_PALETTE[3],
        "China": _LEGACY_STYLE_PALETTE[3],
        "CN": _LEGACY_STYLE_PALETTE[3],
        "KR": _LEGACY_STYLE_PALETTE[4],
        "Korea": _LEGACY_STYLE_PALETTE[4],
        "UK": _LEGACY_STYLE_PALETTE[5],
        "GB": _LEGACY_STYLE_PALETTE[5],
        "World": "#f8fafc",
        "Aggregate": "#f8fafc",
        "Total": "#f8fafc",
        "Neutral": "#94a3b8",
        "Secondary": _LEGACY_STYLE_PALETTE[6],
    }
    cleaned = name.split("(")[0].strip()
    if cleaned in fixed:
        return fixed[cleaned]
    return _LEGACY_STYLE_PALETTE[index % len(_LEGACY_STYLE_PALETTE)]


def legacy_add_zero_line(fig: go.Figure) -> go.Figure:
    bg = fig.layout.paper_bgcolor
    is_dark = bg in ["#0d0f12", "black", "#000000"]
    line_color = "rgba(255,255,255,0.4)" if is_dark else "rgba(0,0,0,0.3)"
    fig.add_hline(y=0, line_width=1, line_color=line_color, layer="below")
    return fig


def legacy_get_value_label(series, name: str, fmt: str = ".2f") -> str:
    if series is None or series.dropna().empty:
        return name
    val = float(series.dropna().iloc[-1])
    return f"{name} ({val:{fmt}})"


def df_plot(
    df: pd.DataFrame,
    x: Any = None,
    y: Any = None,
    kind: str = "line",
    title: Optional[str] = None,
    **kwargs: Any,
):
    """Generic plotter for DataFrames used inside custom chart scripts."""
    if kind == "line":
        return px.line(df, x=x, y=y, title=title, **kwargs)
    if kind == "bar":
        return px.bar(df, x=x, y=y, title=title, **kwargs)
    if kind == "scatter":
        return px.scatter(df, x=x, y=y, title=title, **kwargs)
    return px.line(df, title=title)


# ---------------------------------------------------------------------------
# Chart theme application
# ---------------------------------------------------------------------------

def apply_chart_theme(
    fig: Any,
    mode: Optional[str] = None,
    force_dark: Optional[bool] = None,
):
    """Apply the canonical chart theme to a Plotly figure."""
    resolved_mode = mode
    if resolved_mode not in {"light", "dark"}:
        if force_dark is True:
            resolved_mode = "dark"
        elif force_dark is False:
            resolved_mode = "light"
        else:
            resolved_mode = "light"
    return chart_theme.apply(fig, mode=resolved_mode)


# ---------------------------------------------------------------------------
# Code preparation & validation (no HTTPException — callers wrap errors)
# ---------------------------------------------------------------------------

def _import_to_pass(m: re.Match) -> str:
    indent = m.group("indent")
    return f"{indent}pass" if indent else ""


def normalize_legacy_chart_code(code: str) -> str:
    """Strip redundant imports that are already injected into exec scope."""
    normalized = _SCOPE_IMPORT_RE.sub(_import_to_pass, code)
    if normalized != code:
        logger.info("Stripped redundant imports (already injected into exec scope).")
    return normalized


def prepare_custom_chart_code(code: str) -> str:
    """Normalize and validate custom chart code.

    Raises ``UnsafeCustomChartCodeError`` on forbidden syntax.
    """
    normalized = normalize_legacy_chart_code(code)
    validate_custom_chart_code(normalized)
    return normalized


# ---------------------------------------------------------------------------
# Execution scope
# ---------------------------------------------------------------------------

def build_chart_global_scope(db_session=None) -> Dict[str, Any]:
    """Build the sandboxed global scope for chart code execution."""
    from ix.db.query import Series as OriginalSeries, MultiSeries
    from ix.common.data.statistics import Cycle
    from ix.common.data.transforms import (
        MonthEndOffset,
        Offset,
        Clip,
        Diff,
        Ffill,
        MovingAverage,
        PctChange,
        Rebase,
        Resample,
        StandardScalar,
    )
    from ix.common.quantitative.dsl import (
        Correlation as _Correlation,
        RollingCorrelation as _RollingCorrelation,
        Regression as _Regression,
        RollingBeta as _RollingBeta,
        PCA as _PCA,
        VaR as _VaR,
        ExpectedShortfall as _ExpectedShortfall,
    )

    def Series_wrapped(
        code,
        freq=None,
        name=None,
        ccy=None,
        scale=None,
        _skip_fx=False,
        strict=True,
    ):
        return OriginalSeries(
            code,
            freq=freq,
            name=name,
            ccy=ccy,
            scale=scale,
            session=db_session,
            _skip_fx=_skip_fx,
            strict=strict,
        )

    return {
        "pd": pd,
        "np": np,
        "px": px,
        "go": go,
        "make_subplots": make_subplots,
        "Series": Series_wrapped,
        "MultiSeries": MultiSeries,
        "Cycle": Cycle,
        "MonthEndOffset": MonthEndOffset,
        "StandardScalar": StandardScalar,
        "Offset": Offset,
        "Rebase": Rebase,
        "Resample": Resample,
        "PctChange": PctChange,
        "Diff": Diff,
        "MovingAverage": MovingAverage,
        "Clip": Clip,
        "Ffill": Ffill,
        "apply_academic_style": apply_chart_theme,
        "add_zero_line": legacy_add_zero_line,
        "get_value_label": legacy_get_value_label,
        "get_color": legacy_get_color,
        "apply_theme": apply_chart_theme,
        "df_plot": df_plot,
        "Correlation": _Correlation,
        "RollingCorrelation": _RollingCorrelation,
        "Regression": _Regression,
        "RollingBeta": _RollingBeta,
        "PCA": _PCA,
        "VaR": _VaR,
        "ExpectedShortfall": _ExpectedShortfall,
        "datetime": __import__("datetime").datetime,
        "date": __import__("datetime").date,
        "timedelta": __import__("datetime").timedelta,
        "Dict": dict,
        "List": list,
        "Tuple": tuple,
        "Optional": __import__("typing").Optional,
        "__builtins__": SAFE_CUSTOM_CHART_BUILTINS,
        "__name__": "__main__",
    }


# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

class ChartExecutionError(Exception):
    """Raised when custom chart code execution fails."""

    def __init__(self, message: str, error_type: str = "Execution Error"):
        self.error_type = error_type
        super().__init__(message)


def execute_custom_code(code: str, *, validated: bool = False) -> Any:
    """Execute user-provided Python chart code and return figure JSON.

    The code must define a ``fig`` variable containing a Plotly figure.

    Raises:
        UnsafeCustomChartCodeError: If the code contains forbidden syntax.
        ChartExecutionError: If execution fails for other reasons.
    """
    if not validated:
        code = prepare_custom_chart_code(code)

    from ix.db.conn import conn as _conn, ensure_connection as _ensure_conn

    _ensure_conn()
    _db = _conn.SessionLocal()
    try:
        global_scope = build_chart_global_scope(_db)
        exec(code, global_scope)
        fig_result = global_scope.get("fig")
        if fig_result is None:
            for value in global_scope.values():
                if isinstance(value, go.Figure):
                    fig_result = value
                    break
        if fig_result is None:
            raise ChartExecutionError(
                "The code must define a variable named 'fig' containing the Plotly figure.",
                error_type="Validation Error",
            )
        try:
            fig_result = apply_chart_theme(fig_result)
        except Exception as exc:
            logger.debug("Theme apply failed during exec: %s", exc)
        return get_clean_figure_json(fig_result)
    except (UnsafeCustomChartCodeError, ChartExecutionError):
        raise
    except SyntaxError as exc:
        logger.error("Syntax error in custom chart code: %s", exc)
        raise ChartExecutionError(
            f"Syntax error in chart code: {exc}",
            error_type="Syntax Error",
        ) from exc
    except (NameError, ImportError) as exc:
        logger.error("Name/Import error in custom chart code: %s", exc)
        raise ChartExecutionError(
            str(exc),
            error_type=type(exc).__name__,
        ) from exc
    except Exception as exc:
        logger.error("Error executing custom chart code: %s", exc)
        logger.error(traceback.format_exc())
        raise ChartExecutionError(
            "Internal error during chart execution",
            error_type="Internal Error",
        ) from exc
    finally:
        _db.close()
        _conn.Session.remove()


# ---------------------------------------------------------------------------
# Figure serialization
# ---------------------------------------------------------------------------

def simplify_figure(figure_data: Any) -> Any:
    """Recursively convert figure data to standard JSON-safe types."""
    if isinstance(figure_data, dict):
        return {k: simplify_figure(v) for k, v in figure_data.items()}
    elif isinstance(figure_data, list):
        return [simplify_figure(v) for v in figure_data]
    elif isinstance(figure_data, (np.ndarray, np.generic)):
        return figure_data.tolist()
    elif hasattr(figure_data, "to_dict"):
        return simplify_figure(figure_data.to_dict())
    return figure_data


def decode_plotly_binary_arrays(figure_data: Any) -> Any:
    """Decode Plotly JSON typed-array payloads to nested Python lists."""
    if isinstance(figure_data, dict):
        if "bdata" in figure_data and "dtype" in figure_data:
            try:
                raw = base64.b64decode(figure_data["bdata"])
                arr = np.frombuffer(raw, dtype=np.dtype(figure_data["dtype"]))
                shape = figure_data.get("shape")
                if shape:
                    dims = [int(x.strip()) for x in str(shape).split(",") if x.strip()]
                    if dims:
                        arr = arr.reshape(tuple(dims))
                return arr.tolist()
            except Exception as exc:
                logger.debug("ndarray decode failed, keeping original payload: %s", exc)
                return figure_data
        return {k: decode_plotly_binary_arrays(v) for k, v in figure_data.items()}
    if isinstance(figure_data, list):
        return [decode_plotly_binary_arrays(v) for v in figure_data]
    return figure_data


def get_clean_figure_json(fig: Any) -> Any:
    """Serialize a Plotly figure to a JSON-safe dictionary.

    Uses ``pio.to_json`` as the primary engine because it handles
    pandas/numpy dates significantly better than raw ``fig.to_dict()``.
    """

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.ndarray, np.generic)):
                return obj.tolist()
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return super().default(obj)

    try:
        if isinstance(fig, dict):
            clean_json_str = json.dumps(fig, cls=_NumpyEncoder)
            return json.loads(clean_json_str)
        json_str = pio.to_json(fig, engine="json")
        return json.loads(json_str)
    except Exception as e:
        logger.warning(
            "pio.to_json failed in get_clean_figure_json, falling back: %s", e
        )
        fig_dict = fig.to_dict()
        clean_json_str = json.dumps(fig_dict, cls=_NumpyEncoder)
        return json.loads(clean_json_str)


def compact_figure_for_html(figure: Any) -> Dict[str, Any]:
    """Strip non-essential layout keys from a figure dict for HTML export."""
    if not isinstance(figure, dict):
        return {"data": [], "layout": {}}
    data = figure.get("data")
    layout = figure.get("layout")
    frames = figure.get("frames")
    if not isinstance(data, list):
        data = []
    if not isinstance(layout, dict):
        layout = {}
    else:
        layout = dict(layout)
    layout.pop("uirevision", None)
    layout.pop("width", None)
    layout.pop("height", None)
    compact = {"data": data, "layout": layout}
    if isinstance(frames, list) and frames:
        compact["frames"] = frames
    return compact


# ---------------------------------------------------------------------------
# Creator metadata helper
# ---------------------------------------------------------------------------

def creator_metadata(chart: Any) -> Dict[str, Optional[str]]:
    """Extract creator metadata from a Charts ORM object."""
    creator = getattr(chart, "creator", None)
    creator_id = getattr(chart, "created_by_user_id", None)
    creator_email = getattr(creator, "email", None) if creator is not None else None
    first_name = getattr(creator, "first_name", None) if creator is not None else None
    last_name = getattr(creator, "last_name", None) if creator is not None else None
    creator_name = " ".join([x for x in [first_name, last_name] if x]) or None
    return {
        "created_by_user_id": str(creator_id) if creator_id else None,
        "created_by_email": str(creator_email) if creator_email else None,
        "created_by_name": creator_name,
    }


# ---------------------------------------------------------------------------
# Image rendering
# ---------------------------------------------------------------------------

def _build_figure_from_data(raw: Any) -> go.Figure:
    """Rehydrate a Plotly figure from JSON data."""
    if isinstance(raw, str):
        try:
            return pio.from_json(raw, skip_invalid=True)
        except Exception as exc:
            logger.debug("pio.from_json(str) failed, trying json.dumps fallback: %s", exc)
    try:
        return pio.from_json(json.dumps(raw), skip_invalid=True)
    except Exception as exc:
        logger.debug("pio.from_json(json.dumps) failed, using go.Figure fallback: %s", exc)
        return go.Figure(raw, skip_invalid=True)


def _prepare_pdf_figure(fig: go.Figure) -> go.Figure:
    """Scale fonts for PDF readability.

    Does NOT touch margins, autosize, or axis ranges to avoid distorting
    the chart relative to the web view.
    """
    scale = 3.0

    def _sz(current, fallback, minimum):
        return max(minimum, int((current if current else fallback) * scale))

    # Global font
    base = fig.layout.font.size if fig.layout.font and fig.layout.font.size else 11
    fig.update_layout(
        font=dict(size=max(30, int(base * scale))),
    )

    # Scale the chart title
    title_obj = fig.layout.title
    title_text = None
    if title_obj:
        if isinstance(title_obj, str):
            title_text = title_obj
        elif hasattr(title_obj, "text") and title_obj.text:
            title_text = title_obj.text
    if title_text:
        t_size = 14
        if title_obj and hasattr(title_obj, "font") and title_obj.font and title_obj.font.size:
            t_size = title_obj.font.size
        fig.update_layout(
            title=dict(
                text=title_text,
                font=dict(size=max(30, int(t_size * scale))),
            )
        )

    # Axis tick + title fonts
    fig.for_each_xaxis(
        lambda x: x.update(
            tickfont=dict(
                size=_sz(x.tickfont.size if x.tickfont and x.tickfont.size else 0, 11, 28)
            ),
            title=dict(
                font=dict(
                    size=_sz(
                        x.title.font.size
                        if x.title and x.title.font and x.title.font.size
                        else 0,
                        12,
                        30,
                    )
                )
            ),
        )
    )
    fig.for_each_yaxis(
        lambda y: y.update(
            tickfont=dict(
                size=_sz(y.tickfont.size if y.tickfont and y.tickfont.size else 0, 11, 28)
            ),
            title=dict(
                font=dict(
                    size=_sz(
                        y.title.font.size
                        if y.title and y.title.font and y.title.font.size
                        else 0,
                        12,
                        30,
                    )
                )
            ),
        )
    )

    # Legend
    if fig.layout.legend:
        lg = (
            fig.layout.legend.font.size
            if fig.layout.legend.font and fig.layout.legend.font.size
            else 10
        )
        fig.update_layout(legend=dict(font=dict(size=max(26, int(lg * scale)))))

    # Annotations
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            s = ann.font.size if ann.font and ann.font.size else 12
            ann.update(font=dict(size=max(26, int(s * scale))))

    # Trace text (data labels, bar text, etc.)
    for trace in fig.data:
        if getattr(trace, "type", None) == "heatmap":
            tf = getattr(trace, "textfont", None) or {}
            z = getattr(trace, "z", None)
            if not getattr(trace, "text", None) and z is not None:
                try:
                    trace.update(text=np.round(np.array(z, dtype=float), 1).tolist())
                except Exception:
                    pass
            if not getattr(trace, "texttemplate", None):
                trace.update(texttemplate="%{text}")
            trace.update(
                textfont=dict(
                    size=max(28, int((getattr(tf, "size", 12) or 12) * scale))
                )
            )
        else:
            tf = getattr(trace, "textfont", None)
            cs = tf.size if tf and getattr(tf, "size", None) else 12
            try:
                trace.update(textfont=dict(size=max(26, int(cs * scale))))
            except Exception:
                pass

        cb = getattr(trace, "colorbar", None)
        if cb:
            cbs = (
                cb.tickfont.size
                if cb.tickfont and getattr(cb.tickfont, "size", None)
                else 12
            )
            try:
                trace.update(
                    colorbar=dict(tickfont=dict(size=max(26, int(cbs * scale))))
                )
            except Exception:
                pass

    return fig


def render_chart_image(
    figure_data: Dict[str, Any], theme: str = "light"
) -> Optional[bytes]:
    """Render a single chart figure to PNG bytes using Kaleido."""
    try:
        figure_data = chart_theme.apply_json(figure_data, mode=theme)
    except Exception as e:
        logger.warning("Theme application skipped in render_chart_image: %s", e)
    decoded_figure = decode_plotly_binary_arrays(figure_data)

    try:
        fig = _prepare_pdf_figure(_build_figure_from_data(decoded_figure))
        return pio.to_image(fig, format="png", width=2200, height=940, scale=2)
    except Exception as e:
        logger.error("Error rendering chart image: %s", e)
        return None


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def is_pdf_available() -> bool:
    """Check whether the xhtml2pdf dependency is importable."""
    return _pisa is not None


def generate_pdf_buffer(
    charts: List[Any],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    theme: str = "light",
) -> BytesIO:
    """Generate a PDF report from a list of Charts ORM objects.

    Raises ``RuntimeError`` if xhtml2pdf is not installed.
    """
    if _pisa is None:
        raise RuntimeError(
            "PDF export dependency is unavailable. Install `xhtml2pdf` and redeploy."
        )

    buffer = BytesIO()

    # 1. Pre-fetch/Filter valid charts
    valid_charts = [c for c in charts if c.figure]
    if not valid_charts:
        return buffer

    # 2. Render images in parallel
    logger.info("Starting parallel rendering for %d charts...", len(valid_charts))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_index = {
            executor.submit(render_chart_image, chart.figure, theme): i
            for i, chart in enumerate(valid_charts)
        }
        results: List[Optional[bytes]] = [None] * len(valid_charts)
        try:
            completed_renders = 0
            for future in concurrent.futures.as_completed(future_to_index, timeout=600):
                index = future_to_index[future]
                chart_name = valid_charts[index].name
                try:
                    data = future.result()
                    if data:
                        logger.info(
                            "Successfully rendered png for index %d: %s",
                            index,
                            chart_name,
                        )
                    else:
                        logger.warning(
                            "Render returned None for index %d: %s",
                            index,
                            chart_name,
                        )
                    results[index] = data
                    if progress_cb:
                        completed_renders += 1
                        progress_cb(
                            completed_renders,
                            len(valid_charts) * 2,
                            f"Rendering image {completed_renders}/{len(valid_charts)}...",
                        )
                except Exception as e:
                    logger.error(
                        "Parallel rendering failed for chart at index %d (%s): %s",
                        index,
                        chart_name,
                        e,
                    )
                    if progress_cb:
                        completed_renders += 1
                        progress_cb(
                            completed_renders,
                            len(valid_charts) * 2,
                            f"Rendering image {completed_renders}/{len(valid_charts)}...",
                        )
        except concurrent.futures.TimeoutError:
            logger.error("PDF generation timed out waiting for chart renders.")

    # 2b. Validate results
    for i, img_data in enumerate(results):
        if img_data is None:
            chart_name = valid_charts[i].name or f"chart-{i}"
            logger.warning(
                "PDF: chart '%s' rendered as None, substituting placeholder",
                chart_name,
            )
            results[i] = b""

    # 3. Construct PDF using xhtml2pdf
    is_dark = theme.lower() == "dark"
    body_bg = "#0f172a" if is_dark else "#ffffff"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    h1_color = "#f8fafc" if is_dark else "#0f172a"
    meta_color = "#94a3b8" if is_dark else "#64748b"
    desc_color = "#cbd5e1" if is_dark else "#475569"

    nav_accent = "#818cf8" if is_dark else "#4f46e5"
    nav_bg = "#1e293b" if is_dark else "#f1f5f9"
    nav_border = "#334155" if is_dark else "#e2e8f0"
    arrow_color = "#e2e8f0" if is_dark else "#334155"
    arrow_disabled = "#475569" if is_dark else "#cbd5e1"

    total = len(valid_charts)

    html_parts = []
    html_parts.append(
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <style>
            @page {{ size: landscape; margin: 1cm 1.5cm 1cm 1.5cm; }}
            body {{ font-family: 'Courier New', Courier, monospace; background-color: {body_bg}; color: {text_color}; line-height: 1.4; font-size: 10pt; }}
            h2 {{ color: {h1_color}; font-size: 14pt; margin-top: 6px; margin-bottom: 3px; -pdf-outline: true; -pdf-outline-level: 0; }}
            .meta {{ color: {meta_color}; font-size: 8pt; margin-bottom: 3px; }}
            .desc {{ color: {desc_color}; font-size: 9pt; margin-bottom: 6px; font-style: italic; }}
            img {{ max-width: 100%; display: block; margin: 4px auto; }}
            .chart-page {{ page-break-before: always; }}
            .cover {{ text-align: center; padding-top: 160px; }}
            .cover-title {{ font-size: 36pt; font-weight: bold; color: {h1_color}; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="cover">
            <div class="cover-title">Investment-X Dashboard Report</div>
            <br/>
            <span style="color: {meta_color}; font-size: 14pt;">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            <br/><br/>
            <span style="color: {meta_color}; font-size: 12pt;">{total} charts</span>
        </div>
    """
    )

    for i, chart in enumerate(valid_charts):
        title = html.escape(chart.name or "Untitled Analysis")
        category = html.escape(chart.category or "Uncategorized")
        updated = chart.updated_at.strftime("%Y-%m-%d")
        desc = html.escape(chart.description or "").replace("\n", "<br/>")

        prev_link = (
            f'<a href="#chart-{i - 1}" style="color:{arrow_color};text-decoration:none;'
            f'font-size:11pt;font-weight:bold;">&larr; Prev</a>'
            if i > 0
            else f'<span style="color:{arrow_disabled};font-size:11pt;">&larr; Prev</span>'
        )
        next_link = (
            f'<a href="#chart-{i + 1}" style="color:{arrow_color};text-decoration:none;'
            f'font-size:11pt;font-weight:bold;">Next &rarr;</a>'
            if i < total - 1
            else f'<span style="color:{arrow_disabled};font-size:11pt;">Next &rarr;</span>'
        )

        nav_bar = (
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="background-color:{nav_bg};border-bottom:1px solid {nav_border};'
            f'padding:6px 10px;margin-bottom:6px;">'
            f"<tr>"
            f'<td width="80" style="padding:4px 8px;">{prev_link}</td>'
            f'<td style="text-align:center;padding:4px 8px;">'
            f'<span style="font-size:10pt;font-weight:bold;color:{nav_accent};'
            f'letter-spacing:1px;">{category}</span>'
            f'<span style="color:{meta_color};font-size:9pt;">'
            f"&nbsp;&nbsp;|&nbsp;&nbsp;{i + 1} / {total}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;{updated}</span>"
            f"</td>"
            f'<td width="80" style="text-align:right;padding:4px 8px;">{next_link}</td>'
            f"</tr></table>"
        )

        html_parts.append(f'<div class="chart-page">')
        html_parts.append(f'<a name="chart-{i}"></a>')
        html_parts.append(nav_bar)
        html_parts.append(f"<h2>{title}</h2>")
        if desc:
            html_parts.append(f'<div class="desc">{desc}</div>')

        img_bytes = results[i]
        if img_bytes:
            b64_chart = base64.b64encode(img_bytes).decode("utf-8")
            html_parts.append(f'<img src="data:image/png;base64,{b64_chart}" />')
        else:
            html_parts.append(
                f'<div class="meta" style="color: red;">[Chart rendering failed]</div>'
            )

        html_parts.append("</div>")

        if progress_cb:
            progress_cb(
                len(valid_charts) + i + 1,
                len(valid_charts) * 2,
                f"Assembling PDF page {i + 1}/{len(valid_charts)}...",
            )

    html_parts.append("</body></html>")
    final_html = "".join(html_parts)

    pisa_status = _pisa.CreatePDF(final_html, dest=buffer)
    if pisa_status.err:
        logger.error("pisa.CreatePDF failed")

    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# HTML export builder
# ---------------------------------------------------------------------------

def build_html_export(
    charts: List[Any],
    theme: str = "light",
) -> str:
    """Build a standalone HTML portfolio document from chart ORM objects.

    Returns the full HTML string ready to serve as a download.
    """
    is_dark_html = theme.lower() == "dark"
    _body_bg = "#02040a" if is_dark_html else "#f8fafc"
    _body_color = "#94a3b8" if is_dark_html else "#475569"
    _header_border = (
        "rgba(255,255,255,0.05)" if is_dark_html else "rgba(0,0,0,0.07)"
    )
    _h1_color = "#f8fafc" if is_dark_html else "#0f172a"
    _card_bg = "rgba(255,255,255,0.02)" if is_dark_html else "#ffffff"
    _card_border = "rgba(255,255,255,0.05)" if is_dark_html else "rgba(0,0,0,0.08)"
    _card_shadow = (
        "0 10px 30px -10px rgba(0,0,0,0.5)"
        if is_dark_html
        else "0 2px 12px -4px rgba(0,0,0,0.08)"
    )
    _chart_hdr_bg = "rgba(0,0,0,0.2)" if is_dark_html else "#f1f5f9"
    _chart_hdr_border = (
        "rgba(255,255,255,0.03)" if is_dark_html else "rgba(0,0,0,0.06)"
    )
    _chart_title_color = "#e2e8f0" if is_dark_html else "#0f172a"
    _js_font_color = "#94a3b8" if is_dark_html else "#334155"
    _js_axis_line = (
        "rgba(148,163,184,0.45)" if is_dark_html else "rgba(71,85,105,0.35)"
    )
    _js_tick_color = "#cbd5e1" if is_dark_html else "#475569"

    html_parts = []
    html_parts.append(
        f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Investment-X Research Portfolio</title>
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{
                background-color: {_body_bg};
                color: {_body_color};
                font-family: 'JetBrains Mono', 'Courier New', monospace;
                margin: 0;
                padding: 40px 20px;
                line-height: 1.6;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            header {{ margin-bottom: 60px; border-bottom: 1px solid {_header_border}; padding-bottom: 30px; }}
            h1 {{ color: {_h1_color}; font-weight: 800; letter-spacing: -0.02em; margin: 0; font-family: 'JetBrains Mono', 'Courier New', monospace; }}
            .subtitle {{ font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 0.2em; color: #6366f1; margin-top: 8px; }}
            .chart-card {{
                background: {_card_bg};
                border: 1px solid {_card_border};
                border-radius: 20px;
                margin-bottom: 40px;
                overflow: hidden;
                box-shadow: {_card_shadow};
            }}
            .chart-header {{ padding: 24px 30px; border-bottom: 1px solid {_chart_hdr_border}; background: {_chart_hdr_bg}; }}
            .chart-title {{ font-size: 18px; font-weight: 600; color: {_chart_title_color}; margin: 0; }}
            .chart-meta {{ font-size: 11px; color: #64748b; margin-top: 4px; }}
            .chart-body {{ padding: 20px; min-height: 500px; }}
            .chart-desc {{ padding: 0 30px 30px 30px; font-size: 14px; font-weight: 300; color: #64748b; }}
            footer {{ text-align: center; margin-top: 100px; font-size: 10px; opacity: 0.4; font-family: 'JetBrains Mono'; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Research Intelligence Portfolio</h1>
                <div class="subtitle">Proprietary Models &bull; Investment-X Engine</div>
            </header>
    """
    )

    for i, chart in enumerate(charts):
        clean_name = html.escape(chart.name or "Untitled", quote=True)
        category = html.escape((chart.category or "General").upper(), quote=True)
        date_str = (
            chart.updated_at.strftime("%Y-%m-%d %H:%M")
            if getattr(chart, "updated_at", None)
            else "-"
        )
        desc = html.escape(
            chart.description or "Analysis pending.", quote=True
        ).replace("\n", "<br/>")

        div_id = f"chart_{i}"

        themed_figure = chart_theme.apply_json(chart.figure, mode=theme)
        fig_json = json_dumps_fast(compact_figure_for_html(themed_figure))

        html_parts.append(
            f"""
            <div class="chart-card">
                <div class="chart-header">
                    <h2 class="chart-title">{clean_name}</h2>
                    <div class="chart-meta">{category} &bull; UPDATED {date_str}</div>
                </div>
                <div id="{div_id}" class="chart-body"></div>
                <div class="chart-desc">{desc}</div>
                <script type="text/javascript">
                    (function() {{
                        var fig = {fig_json};
                        fig.layout = fig.layout || {{}};
                        fig.layout.paper_bgcolor = 'rgba(0,0,0,0)';
                        fig.layout.plot_bgcolor = 'rgba(0,0,0,0)';
                        fig.layout.font = {{ color: '{_js_font_color}', family: "'JetBrains Mono', 'Courier New', monospace" }};
                        fig.layout.autosize = true;
                        var axisKeyRe = /^(xaxis|yaxis)(\\d+)?$/;
                        Object.keys(fig.layout).forEach(function(key) {{
                            if (!axisKeyRe.test(key)) return;
                            var axis = Object.assign({{}}, fig.layout[key] || {{}});
                            axis.linecolor = '{_js_axis_line}';
                            axis.showline = axis.showline !== false;
                            axis.mirror = axis.mirror !== false;
                            axis.tickfont = Object.assign({{ color: '{_js_tick_color}', size: 11 }}, axis.tickfont || {{}});
                            if (key.indexOf('yaxis') === 0) {{
                                axis.showticklabels = true;
                                axis.automargin = true;
                                axis.ticklabelposition = axis.ticklabelposition || 'outside';
                            }}
                            fig.layout[key] = axis;
                        }});
                        fig.layout.margin = Object.assign({{ l: 88, r: 20, t: 28, b: 32 }}, fig.layout.margin || {{}});
                        if (typeof fig.layout.margin.l !== 'number' || fig.layout.margin.l < 88) {{
                            fig.layout.margin.l = 88;
                        }}
                        (fig.data || []).forEach(function(t) {{
                            if (t && t.type === 'heatmap') {{
                                if (!t.texttemplate && t.text) t.texttemplate = '<b>%{{text}}</b>';
                                t.textfont = Object.assign({{color: '{_js_font_color}', size: 10, family: "'JetBrains Mono', 'Courier New', monospace"}}, t.textfont || {{}});
                            }}
                        }});
                        Plotly.newPlot('{div_id}', fig.data, fig.layout, {{
                            responsive: true,
                            displayModeBar: 'hover',
                            displaylogo: false
                        }});
                    }})();
                </script>
            </div>
        """
        )

    html_parts.append(
        f"""
            <footer>
                &copy; {datetime.now().year} INVESTMENT-X. ALL RIGHTS RESERVED. BUNDLED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </footer>
        </div>
    </body>
    </html>
    """
    )

    return "".join(html_parts)
