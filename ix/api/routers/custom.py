from fastapi import APIRouter, Depends, HTTPException, Body, Form, Response, Request
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy import func, or_
from typing import List, Optional, Any, Dict, Callable
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import html
import re
import traceback
import concurrent.futures
import base64
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import utils
import textwrap
import sys

from ix.db.conn import get_session
from ix.db.models import Charts, User
from ix.api.dependencies import get_current_user, user_role as _user_role, is_owner_role as _is_owner, is_admin_role as _is_admin, user_id_str as _user_id
from ix.misc import get_logger
from ix.misc.theme import chart_theme, theme_figure_for_delivery as _theme_figure_for_delivery
from ix.utils.safe_custom_code import (
    SAFE_CUSTOM_CHART_BUILTINS,
    UnsafeCustomChartCodeError,
    validate_custom_chart_code,
)

from ix.api.task_utils import start_process, update_process, ProcessStatus


logger = get_logger(__name__)

router = APIRouter()

from ix.api.rate_limit import limiter as _limiter

try:
    import orjson as _orjson
except ImportError:
    _orjson = None

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None


_SCOPE_IMPORT_RE = re.compile(
    r"^(?P<indent>\s*)(?:from\s+(?:ix|ix\.\w+(?:\.\w+)*|plotly|plotly\.\w+|datetime|typing)\s+import\s+[^\n]+|import\s+(?:numpy|pandas|plotly|datetime|time)(?:\.\w+)*(?:\s+as\s+\w+)?)\s*$",
    flags=re.MULTILINE,
)

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


def _json_dumps_fast(payload: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(payload).decode("utf-8")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _require_pdf_dependency() -> None:
    if pisa is None:
        raise HTTPException(
            status_code=503,
            detail="PDF export dependency is unavailable. Install `xhtml2pdf` and redeploy.",
        )


def _legacy_get_color(name: str, index: int = 0) -> str:
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


def _legacy_add_zero_line(fig: go.Figure) -> go.Figure:
    bg = fig.layout.paper_bgcolor
    is_dark = bg in ["#0d0f12", "black", "#000000"]
    line_color = "rgba(255,255,255,0.4)" if is_dark else "rgba(0,0,0,0.3)"
    fig.add_hline(y=0, line_width=1, line_color=line_color, layer="below")
    return fig


def _legacy_get_value_label(series, name: str, fmt: str = ".2f") -> str:
    if series is None or series.dropna().empty:
        return name
    val = float(series.dropna().iloc[-1])
    return f"{name} ({val:{fmt}})"


def _import_to_pass(m: re.Match) -> str:
    indent = m.group("indent")
    return f"{indent}pass" if indent else ""


def _normalize_legacy_chart_code(code: str) -> str:
    normalized = _SCOPE_IMPORT_RE.sub(_import_to_pass, code)
    if normalized != code:
        logger.info("Stripped redundant imports (already injected into exec scope).")
    return normalized


def _prepare_custom_chart_code(code: str) -> str:
    normalized = _normalize_legacy_chart_code(code)
    try:
        validate_custom_chart_code(normalized)
    except UnsafeCustomChartCodeError as exc:
        logger.warning("Rejected unsafe custom chart code: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation Error",
                "message": "Chart code contains forbidden syntax. Please review and try again.",
            },
        ) from exc
    return normalized


def _compact_figure_for_html(figure: Any) -> Dict[str, Any]:
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
    # Keep template to preserve per-chart axis defaults in exported HTML.
    layout.pop("uirevision", None)
    layout.pop("width", None)
    layout.pop("height", None)
    compact = {"data": data, "layout": layout}
    if isinstance(frames, list) and frames:
        compact["frames"] = frames
    return compact


def _creator_metadata(chart: Charts) -> Dict[str, Optional[str]]:
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


def _to_custom_chart_response(chart: Charts):
    payload = ChartResponse.from_orm(chart)
    payload.figure = _theme_figure_for_delivery(chart.figure)
    creator_meta = _creator_metadata(chart)
    payload.created_by_user_id = creator_meta["created_by_user_id"]
    payload.created_by_email = creator_meta["created_by_email"]
    payload.created_by_name = creator_meta["created_by_name"]
    return payload



def _is_chart_owner(chart: Charts, user: User) -> bool:
    chart_owner_id = str(getattr(chart, "created_by_user_id", "") or "")
    return bool(chart_owner_id and chart_owner_id == _user_id(user))


def _can_edit_chart(chart: Charts, user: User) -> bool:
    if _is_owner(user):
        return True
    if _is_admin(user):
        return True
    return _is_chart_owner(chart, user)


def _can_view_chart(chart: Charts, user: User) -> bool:
    return (
        bool(getattr(chart, "public", False))
        or _is_owner(user)
        or _is_admin(user)
        or _is_chart_owner(chart, user)
    )


def _assert_owner_only(
    user: User, detail: str = "Only owner can perform this action."
) -> None:
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail=detail)


def _assert_can_create_chart(user: User) -> None:
    role = _user_role(user)
    if role == User.ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin role is refresh-only for chart operations.",
        )


# --- Pydantic Models ---


class ChartCreate(BaseModel):
    name: str = "Untitled Analysis"
    code: str
    category: Optional[str] = "Personal"
    description: Optional[str] = None
    tags: List[str] = []
    public: bool = True
    chart_style: Optional[str] = None


class ChartUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    public: Optional[bool] = None
    chart_style: Optional[str] = None


class PublicToggle(BaseModel):
    """Toggle public flag for one or more charts."""

    ids: List[str]
    public: bool


class ChartResponse(BaseModel):
    id: str
    name: Optional[str]
    code: str
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    figure: Optional[Dict[str, Any]]
    chart_style: Optional[str] = None
    public: bool = True
    rank: int = 0
    created_by_user_id: Optional[str] = None
    created_by_email: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChartListItemResponse(BaseModel):
    id: str
    name: Optional[str]
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    public: bool = True
    rank: int = 0
    created_by_user_id: Optional[str] = None
    created_by_email: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    code: Optional[str] = None
    figure: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CodePreviewRequest(BaseModel):
    code: str


class ChartReorderItem(BaseModel):
    id: str


class ReorderRequest(BaseModel):
    items: List[ChartReorderItem]


class PDFExportRequest(BaseModel):
    items: List[str]  # List of IDs in order
    theme: str = "light"  # "light" or "dark"


# --- Helper Functions ---


def _to_custom_chart_list_item(
    chart: Charts,
    include_code: bool = False,
    include_figure: bool = False,
) -> ChartListItemResponse:
    creator_meta = _creator_metadata(chart)
    payload: Dict[str, Any] = {
        "id": str(chart.id),
        "name": chart.name,
        "category": chart.category,
        "description": chart.description,
        "tags": chart.tags or [],
        "public": bool(chart.public),
        "rank": int(chart.rank or 0),
        "created_by_user_id": creator_meta["created_by_user_id"],
        "created_by_email": creator_meta["created_by_email"],
        "created_by_name": creator_meta["created_by_name"],
        "created_at": chart.created_at,
        "updated_at": chart.updated_at,
    }
    if include_code:
        payload["code"] = chart.code
    if include_figure:
        payload["figure"] = _theme_figure_for_delivery(chart.figure)
    return ChartListItemResponse(**payload)


def _load_explicit_export_charts(
    db: Session,
    current_user: User,
    requested_ids: List[str],
    *columns: Any,
) -> List[Any]:
    if not requested_ids:
        return []

    query = db.query(*columns) if columns else db.query(Charts)
    charts = query.filter(Charts.id.in_(requested_ids)).all()
    chart_map = {str(chart.id): chart for chart in charts}

    missing_ids = [chart_id for chart_id in requested_ids if chart_id not in chart_map]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Chart not found")

    ordered = [chart_map[chart_id] for chart_id in requested_ids]
    if any(not _can_view_chart(chart, current_user) for chart in ordered):
        raise HTTPException(status_code=404, detail="Chart not found")

    return ordered


def _df_plot(
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


def _custom_chart_apply_theme(
    fig: Any,
    mode: Optional[str] = None,
    force_dark: Optional[bool] = None,
):
    resolved_mode = mode
    if resolved_mode not in {"light", "dark"}:
        if force_dark is True:
            resolved_mode = "dark"
        elif force_dark is False:
            resolved_mode = "light"
        else:
            resolved_mode = "light"
    return chart_theme.apply(fig, mode=resolved_mode)


def _build_custom_chart_global_scope(db_session: Optional[Session]) -> Dict[str, Any]:
    from ix.db.query import Series as OriginalSeries, MultiSeries
    from ix.core.quantitative.statistics import Cycle
    from ix.core.transforms import (
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
    from ix.core.quantitative.dsl import (
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
        "apply_academic_style": _custom_chart_apply_theme,
        "add_zero_line": _legacy_add_zero_line,
        "get_value_label": _legacy_get_value_label,
        "get_color": _legacy_get_color,
        "apply_theme": _custom_chart_apply_theme,
        "df_plot": _df_plot,
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


def execute_custom_code(code: str, *, validated: bool = False):
    """
    Executes user-provided Python code in-process.
    Expected contract: The code must define a 'fig' variable OR return a Plotly figure.
    """
    code = code if validated else _prepare_custom_chart_code(code)
    try:
        from ix.db.conn import conn as _conn, ensure_connection as _ensure_conn
        _ensure_conn()
        _db = _conn.SessionLocal()
        try:
            global_scope = _build_custom_chart_global_scope(_db)
            exec(code, global_scope)
            fig_result = global_scope.get("fig")
            if fig_result is None:
                for value in global_scope.values():
                    if isinstance(value, go.Figure):
                        fig_result = value
                        break
            if fig_result is None:
                raise ValueError("The code must define a variable named 'fig' containing the Plotly figure.")
            try:
                fig_result = _custom_chart_apply_theme(fig_result)
            except Exception as exc:
                logger.debug("Theme apply failed during exec: %s", exc)
            return get_clean_figure_json(fig_result)
        finally:
            _db.close()
    except Exception as exc:
        if isinstance(exc, UnsafeCustomChartCodeError):
            logger.warning("Rejected unsafe custom chart code during execution: %s", exc)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Validation Error",
                    "message": "Chart code contains forbidden syntax. Please review and try again.",
                },
            ) from exc
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, SyntaxError):
            logger.error("Syntax error in custom chart code: %s", exc)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Syntax Error",
                    "message": f"Syntax error in chart code: {exc}",
                },
            ) from exc
        if isinstance(exc, (NameError, ImportError)):
            logger.error("Name/Import error in custom chart code: %s", exc)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

        logger.error("Error executing custom chart code: %s", exc)
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Error",
                "message": "Internal error during chart execution",
            },
        ) from exc



def simplify_figure(figure_data: Any) -> Any:
    """
    Recursively converts figure data to standard JSON-safe types.
    """
    import numpy as np

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
    """
    Decode Plotly JSON typed-array payloads:
    {"bdata": "...", "dtype": "f8", "shape": "16, 5"} -> nested Python lists.
    """
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
                # If decoding fails, keep original payload so rendering can still try fallback paths.
                logger.debug("ndarray decode failed, keeping original payload: %s", exc)
                return figure_data
        return {k: decode_plotly_binary_arrays(v) for k, v in figure_data.items()}
    if isinstance(figure_data, list):
        return [decode_plotly_binary_arrays(v) for v in figure_data]
    return figure_data


def get_clean_figure_json(fig: Any) -> Any:
    """
    Serializes a Plotly figure to a dictionary, ensuring dates are strings and no binary data exists.
    Uses pio.to_json as the primary engine because it handles pandas/numpy dates significantly
    better (as ISO strings) than the raw fig.to_dict() approach.
    """

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.ndarray, np.generic)):
                return obj.tolist()
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return super().default(obj)

    try:
        if isinstance(fig, dict):
            clean_json_str = json.dumps(fig, cls=NumpyEncoder)
            return json.loads(clean_json_str)
        # pio.to_json correctly converts pandas/numpy Timestamps to ISO strings
        json_str = pio.to_json(fig, engine="json")
        return json.loads(json_str)
    except Exception as e:
        logger.warning(
            f"pio.to_json failed in get_clean_figure_json, falling back: {e}"
        )
        # Fallback to dictionary conversion and manual encoding
        fig_dict = fig.to_dict()
        clean_json_str = json.dumps(fig_dict, cls=NumpyEncoder)
        return json.loads(clean_json_str)


def render_chart_image(
    figure_data: Dict[str, Any], theme: str = "light"
) -> Optional[bytes]:
    """Helper to render a single chart figure to PNG bytes using Kaleido PlotlyScope."""
    # Apply the requested theme before rendering (overrides stored theme)
    try:
        figure_data = chart_theme.apply_json(figure_data, mode=theme)
    except Exception as e:
        logger.warning(f"Theme application skipped in render_chart_image: {e}")
    decoded_figure = decode_plotly_binary_arrays(figure_data)

    def _build_figure(raw: Any) -> go.Figure:
        # Rehydrate from Plotly JSON first; this preserves encoded arrays better than go.Figure(raw)
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
        """Increase typography and spacing for PDF readability."""
        base_font = 40
        if fig.layout.font and fig.layout.font.size:
            base_font = max(40, int(fig.layout.font.size * 2.5))
        fig.update_layout(
            font=dict(size=base_font, family="Courier New, Courier, monospace"),
            margin=dict(l=150, r=100, t=150, b=120),
            autosize=False,
        )

        # Ensure chart/axis text remains legible after page scaling.
        fig.for_each_xaxis(
            lambda x: x.update(
                tickfont=dict(
                    size=max(
                        35,
                        int(
                            x.tickfont.size * 2.5
                            if x.tickfont and x.tickfont.size
                            else 30
                        ),
                    )
                ),
                title=dict(
                    font=dict(
                        size=max(
                            40,
                            int(
                                x.title.font.size * 2.5
                                if x.title and x.title.font and x.title.font.size
                                else 35
                            ),
                        )
                    )
                ),
            )
        )
        fig.for_each_yaxis(
            lambda y: y.update(
                tickfont=dict(
                    size=max(
                        35,
                        int(
                            y.tickfont.size * 2.5
                            if y.tickfont and y.tickfont.size
                            else 30
                        ),
                    )
                ),
                title=dict(
                    font=dict(
                        size=max(
                            40,
                            int(
                                y.title.font.size * 2.5
                                if y.title and y.title.font and y.title.font.size
                                else 35
                            ),
                        )
                    )
                ),
            )
        )
        # Remove Plotly's own title — the PDF HTML template provides h2 titles
        fig.update_layout(title=None)
        # Reclaim the top margin since there's no title
        fig.update_layout(margin=dict(t=80))

        if fig.layout.legend:
            legend_size = 32
            if fig.layout.legend.font and fig.layout.legend.font.size:
                legend_size = max(32, int(fig.layout.legend.font.size * 2.5))
            fig.update_layout(legend=dict(font=dict(size=legend_size)))

        # Scale up annotations (data labels, callouts, etc.)
        if fig.layout.annotations:
            for ann in fig.layout.annotations:
                ann_size = 12
                if ann.font and ann.font.size:
                    ann_size = ann.font.size
                ann.update(font=dict(size=max(28, int(ann_size * 2.5))))

        # Scale up ALL trace text (data labels, bar text, scatter text, etc.)
        for trace in fig.data:
            trace_type = getattr(trace, "type", None)
            if trace_type == "heatmap":
                textfont = getattr(trace, "textfont", None) or {}
                z_data = getattr(trace, "z", None)
                if not getattr(trace, "text", None) and z_data is not None:
                    try:
                        trace.update(
                            text=np.round(np.array(z_data, dtype=float), 1).tolist()
                        )
                    except Exception as exc:
                        logger.debug("Heatmap text rounding failed: %s", exc)
                if not getattr(trace, "texttemplate", None):
                    trace.update(texttemplate="%{text}")
                trace.update(
                    textfont=dict(
                        size=max(35, int((getattr(textfont, "size", 12) or 12) * 2.5))
                    )
                )
            else:
                # Bar, scatter, pie, waterfall, funnel, treemap, etc.
                textfont = getattr(trace, "textfont", None)
                current_size = 12
                if textfont and getattr(textfont, "size", None):
                    current_size = textfont.size
                try:
                    trace.update(
                        textfont=dict(size=max(28, int(current_size * 2.5)))
                    )
                except Exception as exc:
                    logger.debug("Trace textfont scaling failed: %s", exc)

            # Scale colorbar tick labels if present
            colorbar = getattr(trace, "colorbar", None)
            if colorbar:
                cb_size = 12
                if colorbar.tickfont and getattr(colorbar.tickfont, "size", None):
                    cb_size = colorbar.tickfont.size
                try:
                    trace.update(
                        colorbar=dict(
                            tickfont=dict(size=max(28, int(cb_size * 2.5)))
                        )
                    )
                except Exception as exc:
                    logger.debug("Colorbar tickfont scaling failed: %s", exc)

        return fig

    try:
        fig = _prepare_pdf_figure(_build_figure(decoded_figure))
        return pio.to_image(fig, format="png", width=2200, height=1300, scale=2)
    except Exception as e:
        logger.error(f"Error rendering chart image: {e}")
        return None


def generate_pdf_buffer(
    charts: List[Charts],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    theme: str = "light",
) -> BytesIO:
    _require_pdf_dependency()
    buffer = BytesIO()

    # 1. Pre-fetch/Filter valid charts
    valid_charts = []
    for chart in charts:
        if chart.figure:
            valid_charts.append(chart)

    if not valid_charts:
        return buffer

    # 2. Render images in parallel
    chart_images = []
    logger.info(f"Starting parallel rendering for {len(valid_charts)} charts...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_index = {
            executor.submit(render_chart_image, chart.figure, theme): i
            for i, chart in enumerate(valid_charts)
        }
        results = [None] * len(valid_charts)
        try:
            completed_renders = 0
            for future in concurrent.futures.as_completed(future_to_index, timeout=600):
                index = future_to_index[future]
                chart_name = valid_charts[index].name
                try:
                    data = future.result()
                    if data:
                        logger.info(
                            f"Successfully rendered png for index {index}: {chart_name}"
                        )
                    else:
                        logger.warning(
                            f"Render returned None for index {index}: {chart_name}"
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
                        f"Parallel rendering failed for chart at index {index} ({chart_name}): {e}"
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

    # 3. Construct PDF using xhtml2pdf
    is_dark = theme.lower() == "dark"
    body_bg = "#0f172a" if is_dark else "#ffffff"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    h1_color = "#f8fafc" if is_dark else "#0f172a"
    meta_color = "#94a3b8" if is_dark else "#64748b"
    desc_color = "#cbd5e1" if is_dark else "#475569"

    # Navigation bar colors
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

        # Build top nav bar: [< Prev]  Category  |  3 / 25  |  Updated  [Next >]
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

    pisa_status = pisa.CreatePDF(final_html, dest=buffer)
    if pisa_status.err:
        logger.error("pisa.CreatePDF failed")

    buffer.seek(0)
    return buffer


# --- Endpoints ---


@router.post("/custom/preview")
@_limiter.limit("10/minute")
def preview_custom_chart(
    request: Request,
    body: CodePreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Executes code and returns the figure JSON without saving.
    """
    import time
    from fastapi.responses import Response

    start_time = time.time()
    logger.info(f"Previewing custom chart. Code length: {len(body.code)}")

    try:
        code = body.code if getattr(body, '_validated', False) else _prepare_custom_chart_code(body.code)
        # Run directly in-process (no multiprocessing) for reliability
        from ix.db.conn import conn as _conn, ensure_connection as _ensure_conn
        _ensure_conn()
        _db = _conn.SessionLocal()
        try:
            global_scope = _build_custom_chart_global_scope(_db)
            exec(code, global_scope)
            fig_result = global_scope.get("fig")
            if fig_result is None:
                for key, value in global_scope.items():
                    if isinstance(value, go.Figure):
                        fig_result = value
                        break
            if fig_result is None:
                raise ValueError("The code must define a variable named 'fig' containing the Plotly figure.")
            try:
                fig_result = _custom_chart_apply_theme(fig_result)
            except Exception as exc:
                logger.debug("Theme apply failed during batch preview: %s", exc)
            fig = get_clean_figure_json(fig_result)
        finally:
            _db.close()

        exec_duration = time.time() - start_time
        logger.info(f"Chart execution completed in {exec_duration:.2f}s")
    except Exception as e:
        exec_duration = time.time() - start_time
        logger.error(f"Execution failed after {exec_duration:.2f}s: {e}")
        if isinstance(e, HTTPException):
            raise e

        logger.error(traceback.format_exc())

        raise HTTPException(
            status_code=400,
            detail={
                "error": "Execution Error",
                "message": str(e),
            },
        )

    try:
        serial_start = time.time()
        if isinstance(fig, dict):
            json_str = _json_dumps_fast(fig)
        else:
            json_str = pio.to_json(fig)

        serial_duration = time.time() - serial_start
        total_duration = time.time() - start_time
        logger.info(
            f"Chart preview complete. exec={exec_duration:.2f}s serial={serial_duration:.2f}s "
            f"total={total_duration:.2f}s size={len(json_str)} bytes"
        )

        # Return directly as JSON response to avoid double serialization
        return Response(content=json_str, media_type="application/json")
    except Exception as e:
        logger.error(f"Failed to serialize figure: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail="Failed to serialize figure to JSON"
        )


@router.post("/custom", response_model=ChartResponse)
@_limiter.limit("10/minute")
def create_custom_chart(
    request: Request,
    chart_data: ChartCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom chart."""
    _assert_can_create_chart(current_user)
    logger.info(f"Creating new chart with name: '{chart_data.name}'")
    normalized_code = _prepare_custom_chart_code(chart_data.code)

    # Optional: Validate code by running it once?
    # Let's render it to get the initial figure cache
    try:
        fig = execute_custom_code(normalized_code, validated=True)
        figure_json = get_clean_figure_json(fig)
    except Exception as exc:
        logger.debug("Initial figure render failed for new chart '%s': %s", chart_data.name, exc)
        figure_json = None

    # Determine next rank
    max_rank = db.query(func.max(Charts.rank)).scalar() or 0
    next_rank = max_rank + 1

    new_chart = Charts(
        name=chart_data.name,
        code=normalized_code,
        category=chart_data.category,
        description=chart_data.description,
        tags=chart_data.tags,
        figure=figure_json,
        chart_style=chart_data.chart_style,
        public=chart_data.public,
        rank=next_rank,
        created_by_user_id=_user_id(current_user) or None,
    )

    db.add(new_chart)
    try:
        db.commit()
        db.refresh(new_chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while creating chart '%s'", chart_data.name)
        raise HTTPException(status_code=500, detail="Failed to save chart")
    logger.info(f"New chart created with ID: {new_chart.id}, Name: '{new_chart.name}'")
    return _to_custom_chart_response(new_chart)


@router.get("/custom", response_model=List[ChartListItemResponse])
def list_custom_charts(
    response: Response,
    include_code: bool = False,
    include_figure: bool = False,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all custom charts (shared across admins)."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    query = db.query(Charts).options(
        joinedload(Charts.creator).load_only(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
        )
    )
    if not (_is_owner(current_user) or _is_admin(current_user)):
        query = query.filter(
            or_(
                Charts.created_by_user_id == _user_id(current_user),
                Charts.public == True,
            )
        )

    # Default list is metadata-only to keep studio opening fast.
    if not include_code and not include_figure:
        query = query.options(
            load_only(
                Charts.id,
                Charts.name,
                Charts.category,
                Charts.description,
                Charts.tags,
                Charts.public,
                Charts.rank,
                Charts.created_by_user_id,
                Charts.created_at,
                Charts.updated_at,
            )
        )
    elif include_code and not include_figure:
        query = query.options(
            load_only(
                Charts.id,
                Charts.name,
                Charts.category,
                Charts.description,
                Charts.tags,
                Charts.public,
                Charts.rank,
                Charts.created_by_user_id,
                Charts.created_at,
                Charts.updated_at,
                Charts.code,
            )
        )
    elif include_figure and not include_code:
        query = query.options(
            load_only(
                Charts.id,
                Charts.name,
                Charts.category,
                Charts.description,
                Charts.tags,
                Charts.public,
                Charts.rank,
                Charts.created_by_user_id,
                Charts.created_at,
                Charts.updated_at,
                Charts.figure,
            )
        )

    charts = query.order_by(Charts.rank.asc(), Charts.created_at.desc()).all()
    return [
        _to_custom_chart_list_item(
            chart,
            include_code=include_code,
            include_figure=include_figure,
        )
        for chart in charts
    ]


@router.put("/custom/reorder")
@_limiter.limit("10/minute")
def reorder_custom_charts(
    request: Request,
    order_data: ReorderRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reorder custom charts based on list of IDs."""
    _assert_owner_only(current_user)

    ids = [item.id for item in order_data.items]

    # Fetch all relevant charts to update
    charts = db.query(Charts).filter(Charts.id.in_(ids)).all()
    chart_map = {str(c.id): c for c in charts}

    for index, chart_id in enumerate(ids):
        if str(chart_id) in chart_map:
            chart_map[str(chart_id)].rank = index

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while reordering charts")
        raise HTTPException(status_code=500, detail="Failed to reorder charts")
    return {"message": "Reordered successfully"}


@router.patch("/custom/public")
@_limiter.limit("10/minute")
def toggle_public(
    request: Request,
    data: PublicToggle,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the public flag for one or more charts."""
    _assert_owner_only(current_user)
    db.query(Charts).filter(Charts.id.in_(data.ids)).update(
        {Charts.public: data.public}, synchronize_session="fetch"
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while toggling public flag")
        raise HTTPException(status_code=500, detail="Failed to update chart visibility")
    return {"message": f"Updated {len(data.ids)} chart(s)"}


@router.post("/custom/pdf")
@_limiter.limit("5/minute")
def export_custom_charts_pdf(
    request: Request,
    items: str = Form(default="[]"),
    theme: str = Form(default="light"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a PDF of charts marked for export, in rank order.

    If request.items is provided, use that order.
    If request.items is empty, auto-select all public charts.
    """
    # Import task registry lazily to avoid circular-import fallback to dummy handlers.
    from ix.api.routers.task import start_process as _start_process
    from ix.api.routers.task import update_process as _update_process
    from ix.api.routers.task import ProcessStatus as _ProcessStatus

    import json

    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            items_list = []
    except json.JSONDecodeError:
        items_list = []
    requested_ids = [str(item) for item in items_list if item]

    user_identifier = str(getattr(current_user, "id", "") or "")
    pid = _start_process("Export PDF Report", user_id=user_identifier)

    try:
        if requested_ids:
            ordered_charts = _load_explicit_export_charts(
                db, current_user, requested_ids
            )
        else:
            # Auto-select all charts flagged for export
            ordered_charts = (
                db.query(Charts)
                .filter(Charts.public.is_(True))
                .order_by(Charts.rank.asc())
                .all()
            )

        if not ordered_charts:
            _update_process(pid, _ProcessStatus.FAILED, "No charts found")
            raise HTTPException(
                status_code=404, detail="No public charts found for PDF export"
            )

        total_steps = max(1, len(ordered_charts) * 2)
        _update_process(
            pid,
            message="Preparing PDF export...",
            progress=f"0/{total_steps}",
        )

        def _on_pdf_progress(current: int, total: int, message: str):
            _update_process(
                pid,
                message=message,
                progress=f"{current}/{max(1, total)}",
            )

        pdf_buffer = generate_pdf_buffer(
            ordered_charts, progress_cb=_on_pdf_progress, theme=theme
        )

        filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        _update_process(
            pid,
            _ProcessStatus.COMPLETED,
            "PDF Generated",
            progress=f"{total_steps}/{total_steps}",
        )

        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"PDF Export failed: {e}")
        _update_process(pid, _ProcessStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail="PDF export failed")


@router.post("/custom/html")
@_limiter.limit("5/minute")
def export_custom_charts_html(
    request: Request,
    items: str = Form(default="[]"),
    theme: str = Form(default="light"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a standalone HTML portfolio of charts marked for export."""
    # Import task registry lazily to avoid circular-import fallback to dummy handlers.
    from ix.api.routers.task import start_process as _start_process
    from ix.api.routers.task import update_process as _update_process
    from ix.api.routers.task import ProcessStatus as _ProcessStatus

    import json

    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            items_list = []
    except json.JSONDecodeError:
        items_list = []
    requested_ids = [str(item) for item in items_list if item]

    user_identifier = str(getattr(current_user, "id", "") or "")
    pid = _start_process("Export Interactive Portfolio", user_id=user_identifier)

    try:
        chart_columns = (
            Charts.id,
            Charts.name,
            Charts.category,
            Charts.description,
            Charts.public,
            Charts.created_by_user_id,
            Charts.updated_at,
            Charts.figure,
        )

        if requested_ids:
            ordered_charts = _load_explicit_export_charts(
                db,
                current_user,
                requested_ids,
                *chart_columns,
            )
        else:
            ordered_charts = (
                db.query(*chart_columns)
                .filter(Charts.public.is_(True))
                .order_by(Charts.rank.asc())
                .all()
            )

        if not ordered_charts:
            _update_process(pid, _ProcessStatus.FAILED, "No charts found")
            raise HTTPException(status_code=404, detail="No charts marked for export")

        _update_process(
            pid, message="Composing HTML bundle...", progress=f"0/{len(ordered_charts)}"
        )

        is_dark_html = theme.lower() == "dark"
        # Theme-dependent CSS values
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
        # JS chart theme values
        _js_font_color = "#94a3b8" if is_dark_html else "#334155"
        _js_axis_line = (
            "rgba(148,163,184,0.45)" if is_dark_html else "rgba(71,85,105,0.35)"
        )
        _js_tick_color = "#cbd5e1" if is_dark_html else "#475569"

        # Build premium HTML bundle
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
                    <div class="subtitle">Proprietary Models • Investment-X Engine</div>
                </header>
        """
        )

        total_charts = len(ordered_charts)
        progress_step = max(1, (total_charts + 11) // 12)

        for i, chart in enumerate(ordered_charts):
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

            # Create a unique ID for Plotly div
            div_id = f"chart_{i}"

            # Apply canonical theme then compact for HTML delivery
            themed_figure = chart_theme.apply_json(chart.figure, mode=theme)
            fig_json = _json_dumps_fast(_compact_figure_for_html(themed_figure))

            html_parts.append(
                f"""
                <div class="chart-card">
                    <div class="chart-header">
                        <h2 class="chart-title">{clean_name}</h2>
                        <div class="chart-meta">{category} • UPDATED {date_str}</div>
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
                            // Keep heatmap labels visible in exported HTML
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
            completed = i + 1
            if completed == total_charts or completed % progress_step == 0:
                _update_process(
                    pid,
                    message=f"Rendering section {completed}/{total_charts}...",
                    progress=f"{completed}/{total_charts}",
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

        full_html = "".join(html_parts)
        filename = (
            f"InvestmentX_Portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        )

        _update_process(
            pid, _ProcessStatus.COMPLETED, "Interactive Portfolio Generated"
        )

        return Response(
            content=full_html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"HTML Export failed: {e}")
        _update_process(pid, _ProcessStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail="HTML export failed")


@router.get("/custom/{chart_id}", response_model=ChartResponse)
def get_custom_chart(
    chart_id: str,
    response: Response,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific custom chart."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    chart = db.query(Charts).filter(Charts.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_view_chart(chart, current_user):
        raise HTTPException(status_code=404, detail="Chart not found")
    return _to_custom_chart_response(chart)


@router.post("/custom/{chart_id}/refresh", response_model=ChartResponse)
@_limiter.limit("10/minute")
def refresh_custom_chart(
    request: Request,
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Re-execute chart code and persist refreshed figure."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # Owner can refresh everything, admin can refresh all, creators can refresh their own.
    can_refresh = (
        _is_owner(current_user)
        or _is_admin(current_user)
        or _is_chart_owner(chart, current_user)
    )
    if not can_refresh:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if not chart.code:
        raise HTTPException(status_code=400, detail="Chart code is missing")

    try:
        fig = execute_custom_code(chart.code)
        chart.figure = get_clean_figure_json(fig)
    except Exception as e:
        logger.error(f"Failed to refresh figure for chart {chart_id}: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Execution Error",
                "message": str(e),
                "traceback": traceback.format_exc(),
            },
        )

    try:
        db.commit()
        db.refresh(chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while refreshing chart %s", chart_id)
        raise HTTPException(status_code=500, detail="Failed to save refreshed chart")
    return _to_custom_chart_response(chart)


@router.put("/custom/{chart_id}", response_model=ChartResponse)
@_limiter.limit("10/minute")
def update_custom_chart(
    request: Request,
    chart_id: str,
    update_data: ChartUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a custom chart."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    old_code_len = len(chart.code) if chart.code else 0
    code_len = len(update_data.code) if update_data.code is not None else "N/A"
    logger.info(
        f"PUT /custom/{chart_id} - New Code Len: {code_len}, Old Code Len: {old_code_len}"
    )

    # Update fields if provided
    if update_data.name is not None:
        logger.info(f"Setting chart name from '{chart.name}' to '{update_data.name}'")
        chart.name = update_data.name
    if update_data.category is not None:
        chart.category = update_data.category
    if update_data.description is not None:
        chart.description = update_data.description
    if update_data.tags is not None:
        chart.tags = update_data.tags
    if update_data.public is not None:
        chart.public = update_data.public
    if update_data.chart_style is not None:
        chart.chart_style = update_data.chart_style

    # If code changes, re-render
    if update_data.code is not None:
        normalized_code = _prepare_custom_chart_code(update_data.code)
        try:
            logger.info(f"Re-executing code for chart {chart_id}...")
            fig = execute_custom_code(normalized_code, validated=True)
            figure_json = get_clean_figure_json(fig)
            chart.code = normalized_code
            chart.figure = figure_json

            # Log a snippet of the figure to verify change
            fig_str = json.dumps(figure_json)[:200]
            logger.info(f"Generated new figure for {chart_id}. Snippet: {fig_str}...")
        except Exception as e:
            logger.error(f"Failed to update figure for chart {chart_id}: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Execution Error",
                    "message": f"Code update rejected because figure generation failed: {str(e)}",
                    "traceback": traceback.format_exc(),
                },
            )

    try:
        db.commit()
        db.refresh(chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while updating chart %s", chart_id)
        raise HTTPException(status_code=500, detail="Failed to save chart update")
    logger.info(
        f"Chart {chart.id} updated successfully. Figure updated: {update_data.code is not None}"
    )
    return _to_custom_chart_response(chart)


@router.delete("/custom/{chart_id}")
@_limiter.limit("10/minute")
def delete_custom_chart(
    request: Request,
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom chart."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db.delete(chart)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while deleting chart %s", chart_id)
        raise HTTPException(status_code=500, detail="Failed to delete chart")
    return {"message": "Chart deleted successfully"}
