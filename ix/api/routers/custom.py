from fastapi import APIRouter, Depends, HTTPException, Body, Response, Request
from fastapi.responses import StreamingResponse
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
import json
import html
import traceback
import concurrent.futures
import base64
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import utils
import textwrap
import sys
import threading
from slowapi import Limiter
from slowapi.util import get_remote_address

from ix.db.conn import get_session
from ix.db.models import CustomChart, User
from ix.api.dependencies import get_current_user
from ix.misc import get_logger
from ix.misc.theme import chart_theme

# Import process manager functions (ensure no circular deps)
try:
    from ix.api.routers.task import start_process, update_process, ProcessStatus
except ImportError:
    # Use dummy functions if import fails (e.g. during circular import check)
    def start_process(name, user_id=None):
        return "dummy"

    def update_process(pid, status=None, message=None, progress=None):
        pass

    class ProcessStatus:
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"


logger = get_logger(__name__)

router = APIRouter()

_limiter = Limiter(key_func=get_remote_address)

try:
    import orjson as _orjson
except Exception:
    _orjson = None


def _theme_figure_for_delivery(figure: Any) -> Any:
    """Apply canonical misc theme when returning figures to dashboard/studio clients."""
    if figure is None:
        return None
    return chart_theme.apply_json(figure, mode="light")


def _json_dumps_fast(payload: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(payload).decode("utf-8")
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


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


def _creator_metadata(chart: CustomChart) -> Dict[str, Optional[str]]:
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


def _to_custom_chart_response(chart: CustomChart):
    payload = CustomChartResponse.from_orm(chart)
    payload.figure = _theme_figure_for_delivery(chart.figure)
    creator_meta = _creator_metadata(chart)
    payload.created_by_user_id = creator_meta["created_by_user_id"]
    payload.created_by_email = creator_meta["created_by_email"]
    payload.created_by_name = creator_meta["created_by_name"]
    return payload


def _user_role(user: User) -> str:
    role = getattr(user, "effective_role", None)
    if callable(role):
        role = role()
    if isinstance(role, str) and role:
        return User.normalize_role(role)
    return User.normalize_role(getattr(user, "role", None))


def _is_owner(user: User) -> bool:
    return _user_role(user) == User.ROLE_OWNER


def _is_admin(user: User) -> bool:
    return _user_role(user) in User.ADMIN_ROLES


def _user_id(user: User) -> str:
    return str(getattr(user, "id", "") or "")


def _is_chart_owner(chart: CustomChart, user: User) -> bool:
    chart_owner_id = str(getattr(chart, "created_by_user_id", "") or "")
    return bool(chart_owner_id and chart_owner_id == _user_id(user))


def _can_edit_chart(chart: CustomChart, user: User) -> bool:
    if _is_owner(user):
        return True
    if _user_role(user) == User.ROLE_ADMIN:
        return False
    return _is_chart_owner(chart, user)


def _can_view_chart(chart: CustomChart, user: User) -> bool:
    return _is_owner(user) or _is_admin(user) or _is_chart_owner(chart, user)


def _assert_owner_only(user: User, detail: str = "Only owner can perform this action.") -> None:
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


class CustomChartCreate(BaseModel):
    name: str = "Untitled Analysis"
    code: str
    category: Optional[str] = "Personal"
    description: Optional[str] = None
    tags: List[str] = []
    public: bool = True
    chart_style: Optional[str] = None


class CustomChartUpdate(BaseModel):
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


class CustomChartResponse(BaseModel):
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


class CustomChartListItemResponse(BaseModel):
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
    chart: CustomChart,
    include_code: bool = False,
    include_figure: bool = False,
) -> CustomChartListItemResponse:
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
    return CustomChartListItemResponse(**payload)


def execute_custom_code(code: str):
    """
    Executes user-provided Python code.
    Expected contract: The code must define a 'fig' variable OR return a Plotly figure.
    WE ARE INJECTING 'df_plot' into the scope.
    """

    # 1. Define the safe/standard plotting helper
    def df_plot(df: pd.DataFrame, x=None, y=None, kind="line", title=None, **kwargs):
        """
        Generic plotter for DataFrames.
        """
        if kind == "line":
            return px.line(df, x=x, y=y, title=title, **kwargs)
        elif kind == "bar":
            return px.bar(df, x=x, y=y, title=title, **kwargs)
        elif kind == "scatter":
            return px.scatter(df, x=x, y=y, title=title, **kwargs)
        # Fallback
        return px.line(df, title=title)

    # 2. Prepare execution context
    import logging

    logger = logging.getLogger("backend")

    from ix.db.conn import conn
    from ix.db.query import (
        Series as OriginalSeries,
        MultiSeries,
        MonthEndOffset,
        StandardScalar,
        Offset,
        Resample,
        PctChange,
        Diff,
        MovingAverage,
        Clip,
        Ffill,
    )
    from ix.cht.style import (
        get_value_label,
        get_color,
        add_zero_line,
    )

    def apply_theme(fig: Any, mode: str | None = None, force_dark: bool | None = None):
        """
        Backward-compatible wrapper around ix.misc.theme chart theme.
        - mode: 'light' or 'dark'
        - force_dark: legacy flag supported by older custom scripts
        """
        resolved_mode = mode
        if resolved_mode not in {"light", "dark"}:
            if force_dark is True:
                resolved_mode = "dark"
            elif force_dark is False:
                resolved_mode = "light"
            else:
                resolved_mode = "light"
        return chart_theme.apply(fig, mode=resolved_mode)

    # Create a single session for all queries in this execution
    # This dramatically improves performance for charts with many tickers
    db_session = None
    try:
        from ix.db.conn import ensure_connection

        ensure_connection()
        db_session = conn.SessionLocal()
    except Exception as e:
        logger.error(f"Error creating DB session for custom chart: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database Error",
                "message": "Could not establish a database session for chart execution.",
                "traceback": str(e),
            },
        )

    # Optimized Series that reuses the session
    def Series_wrapped(code, freq=None, ccy=None):
        return OriginalSeries(code, freq=freq, ccy=ccy, session=db_session)

    # Pre-import common libraries used in Investment-X charts
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    global_scope = {
        "pd": pd,
        "px": px,
        "go": go,
        "make_subplots": make_subplots,
        "Series": Series_wrapped,
        "MultiSeries": MultiSeries,
        "MonthEndOffset": MonthEndOffset,
        "StandardScalar": StandardScalar,
        "Offset": Offset,
        "Resample": Resample,
        "PctChange": PctChange,
        "Diff": Diff,
        "MovingAverage": MovingAverage,
        "Clip": Clip,
        "Ffill": Ffill,
        "get_value_label": get_value_label,
        "get_color": get_color,
        "apply_academic_style": apply_theme,
        "apply_theme": apply_theme,
        "add_zero_line": add_zero_line,
        "df_plot": df_plot,
        "__name__": "__main__",
    }

    # 3. Import common modules for convenience
    try:
        import numpy as np

        global_scope["np"] = np
    except ImportError:
        pass

    try:
        from ix import cht

        global_scope["cht"] = cht
    except ImportError:
        pass

    # 4. Execute
    try:
        # Wrap in a function to allow 'return' statements
        # or just exec.
        # Use single scope for globals/locals to ensure function closures work as expected
        # Enable shared session context for imports
        from ix.db.conn import custom_chart_session

        # Log snippet for debugging
        code_snippet = (code[:100] + "...") if len(code) > 100 else code
        logger.info(f"Executing custom chart code. Snippet: {code_snippet}")

        token = custom_chart_session.set(db_session)
        try:
            exec(code, global_scope)
        finally:
            custom_chart_session.reset(token)

        logger.info("exec() completed successfully.")

        # 5. Extract Figure from the modified scope
        # Check if 'fig' variable is defined
        if "fig" in global_scope:
            logger.info("Found 'fig' variable in scope.")
            fig_result = global_scope["fig"]
        else:
            # Check for any go.Figure in the scope if 'fig' is missing
            fig_result = None
            for key, value in global_scope.items():
                if isinstance(value, go.Figure):
                    logger.info(f"Using alternative figure found in scope: {key}")
                    fig_result = value
                    break

            if fig_result is None:
                logger.error("No figure found in scope after execution.")
                raise ValueError(
                    "The code must define a variable named 'fig' containing the Plotly figure."
                )

        # Enforce the misc chart theme before returning to frontend/storage.
        try:
            fig_result = apply_theme(fig_result)
        except Exception as theme_err:
            logger.warning(f"Theme application skipped due to error: {theme_err}")

        return fig_result

    except BaseException as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error executing custom chart code: {e}")
            logger.error(traceback.format_exc())

            # Determine error details
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.format_exception(exc_type, exc_value, exc_traceback)

            # Provide a more descriptive error message to the frontend as a dict
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Execution Error",
                    "message": str(e),
                    "traceback": "".join(tb),
                },
            )
        else:
            raise e
    finally:
        if db_session:
            db_session.close()
            logger.info("Custom chart DB session closed.")


# Global Kaleido scope to be reused for performance
_KALEIDO_SCOPE = None
_KALEIDO_LOCK = threading.Lock()


def get_kaleido_scope():
    """Returns a singleton PlotlyScope for image rendering."""
    global _KALEIDO_SCOPE
    if _KALEIDO_SCOPE is None:
        with _KALEIDO_LOCK:
            if _KALEIDO_SCOPE is None:
                try:
                    from kaleido.scopes.plotly import PlotlyScope

                    _KALEIDO_SCOPE = PlotlyScope()
                    logger.info("Initialized new Kaleido PlotlyScope.")
                except Exception as e:
                    logger.error(f"Failed to initialize Kaleido scope: {e}")
    return _KALEIDO_SCOPE


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
            except Exception:
                # If decoding fails, keep original payload so rendering can still try fallback paths.
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


def render_chart_image(figure_data: Dict[str, Any], theme: str = "light") -> Optional[bytes]:
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
            except Exception:
                pass
        try:
            return pio.from_json(json.dumps(raw), skip_invalid=True)
        except Exception:
            return go.Figure(raw, skip_invalid=True)

    def _prepare_pdf_figure(fig: go.Figure) -> go.Figure:
        """Increase typography and spacing for PDF readability."""
        base_font = 16
        if fig.layout.font and fig.layout.font.size:
            base_font = max(16, int(fig.layout.font.size))
        fig.update_layout(
            font=dict(size=base_font),
            margin=dict(l=120, r=80, t=120, b=100),
            autosize=False,
        )

        # Ensure chart/axis text remains legible after page scaling.
        fig.for_each_xaxis(
            lambda x: x.update(
                tickfont=dict(size=max(14, (x.tickfont.size if x.tickfont and x.tickfont.size else 12))),
                title=dict(font=dict(size=max(16, (x.title.font.size if x.title and x.title.font and x.title.font.size else 14)))),
            )
        )
        fig.for_each_yaxis(
            lambda y: y.update(
                tickfont=dict(size=max(14, (y.tickfont.size if y.tickfont and y.tickfont.size else 12))),
                title=dict(font=dict(size=max(16, (y.title.font.size if y.title and y.title.font and y.title.font.size else 14)))),
            )
        )
        if fig.layout.title:
            title_size = 20
            if fig.layout.title.font and fig.layout.title.font.size:
                title_size = max(20, int(fig.layout.title.font.size))
            fig.update_layout(title=dict(font=dict(size=title_size)))

        if fig.layout.legend:
            legend_size = 13
            if fig.layout.legend.font and fig.layout.legend.font.size:
                legend_size = max(13, int(fig.layout.legend.font.size))
            fig.update_layout(legend=dict(font=dict(size=legend_size)))

        # Heatmaps often look tiny in PDF exports. Force visible cell labels when present.
        for trace in fig.data:
            if getattr(trace, "type", None) == "heatmap":
                textfont = getattr(trace, "textfont", None) or {}
                z_data = getattr(trace, "z", None)
                if not getattr(trace, "text", None) and z_data is not None:
                    try:
                        trace.update(text=np.round(np.array(z_data, dtype=float), 1).tolist())
                    except Exception:
                        pass
                if not getattr(trace, "texttemplate", None):
                    trace.update(texttemplate="%{text}")
                trace.update(
                    textfont=dict(
                        size=max(14, int(getattr(textfont, "size", 12) or 12))
                    )
                )
        return fig

    try:
        scope = get_kaleido_scope()
        fig = _prepare_pdf_figure(_build_figure(decoded_figure))
        fig_payload = fig.to_plotly_json()
        if not scope:
            logger.error("Kaleido scope not available. Falling back to fig.to_image().")
            return pio.to_image(
                fig, format="png", width=2200, height=1300, scale=2, engine="kaleido"
            )

        # Convert to image bytes using scope directly (more robust than fig.to_image)
        # Use a lock to prevent concurrent access to the same scope instance
        with _KALEIDO_LOCK:
            img_bytes = scope.transform(
                fig_payload, format="png", width=2200, height=1300, scale=2
            )
        return img_bytes
    except Exception as e:
        logger.error(f"Error rendering chart image with PlotlyScope: {e}")
        # Try one last fallback
        try:
            fig = _prepare_pdf_figure(_build_figure(decoded_figure))
            return pio.to_image(
                fig, format="png", width=2200, height=1300, scale=2, engine="kaleido"
            )
        except Exception as fallback_e:
            logger.error(f"Final fallback failed: {fallback_e}")
            return None


def generate_pdf_buffer(
    charts: List[CustomChart],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    theme: str = "light",
) -> BytesIO:
    buffer = BytesIO()
    # Use landscape for charts usually
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    is_dark = theme.lower() == "dark"
    # Theme-based colors for PDF pages
    page_bg_rgb = (11/255, 14/255, 20/255) if is_dark else None   # #0B0E14
    title_rgb = (0.898, 0.914, 0.945) if is_dark else (0.0, 0.0, 0.0)
    meta_rgb = (0.580, 0.639, 0.722) if is_dark else (0.3, 0.3, 0.3)
    desc_rgb = (0.392, 0.455, 0.549) if is_dark else (0.45, 0.45, 0.45)

    # 1. Pre-fetch/Filter valid charts
    valid_charts = []
    for chart in charts:
        if chart.figure:
            valid_charts.append(chart)

    if not valid_charts:
        return buffer

    # 2. Render images in parallel
    # Use ThreadPoolExecutor to run IO/C-extension bound tasks in parallel
    # Kaleido (if used) runs in a separate process, so threads work well here.
    chart_images = []
    logger.info(f"Starting parallel rendering for {len(valid_charts)} charts...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all render tasks
        future_to_index = {
            executor.submit(render_chart_image, chart.figure, theme): i
            for i, chart in enumerate(valid_charts)
        }

        # Initialize results array with None
        results = [None] * len(valid_charts)

        # Collect results with a timeout to prevent hanging the whole process
        try:
            completed_renders = 0
            for future in concurrent.futures.as_completed(future_to_index, timeout=30):
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
                        # First half of progress is image rendering.
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
            # We continue with whatever results we have (None for others)

    # 3. Construct PDF page by page
    for i, chart in enumerate(valid_charts):
        try:
            # Fill page background for dark theme
            if is_dark and page_bg_rgb:
                c.setFillColorRGB(*page_bg_rgb)
                c.rect(0, 0, width, height, fill=1, stroke=0)

            # 1. Render title
            c.setFillColorRGB(*title_rgb)
            c.setFont("Helvetica-Bold", 22)
            title = chart.name or "Untitled Analysis"
            c.drawString(50, height - 50, title)

            # 2. Render meta
            c.setFillColorRGB(*meta_rgb)
            c.setFont("Helvetica", 13)
            meta = f"Category: {chart.category} | Updated: {chart.updated_at.strftime('%Y-%m-%d')}"
            c.drawString(50, height - 70, meta)

            # 3. Render description (wrapped)
            if chart.description:
                c.setFillColorRGB(*desc_rgb)
                c.setFont("Helvetica-Oblique", 12)
                desc_lines = textwrap.wrap(chart.description, width=120)
                y_desc = height - 90
                for line in desc_lines[:3]:  # Limit lines
                    c.drawString(50, y_desc, line)
                    y_desc -= 12

            # 4. Render Chart Image
            img_bytes = results[i]

            if img_bytes:
                img_buffer = BytesIO(img_bytes)
                img = utils.ImageReader(img_buffer)

                # Draw image
                # Provide space below header
                c.drawImage(
                    img,
                    40,
                    50,
                    width=width - 80,
                    height=height - 200,
                    preserveAspectRatio=True,
                )
            else:
                # Fallback for failed render
                c.setFont("Helvetica", 12)
                c.drawString(50, height / 2, "Error: Could not render chart image.")

            if progress_cb:
                # Second half of progress is page assembly.
                progress_cb(
                    len(valid_charts) + i + 1,
                    len(valid_charts) * 2,
                    f"Assembling PDF page {i + 1}/{len(valid_charts)}...",
                )
            c.showPage()

        except Exception as e:
            logger.error(f"Failed to add chart {chart.id} page to PDF: {e}")
            # Ensure we don't break the whole PDF generation for one page error if possible
            # But usually showPage() resets context.
            continue

    c.save()
    buffer.seek(0)
    return buffer


# --- Endpoints ---


@router.post("/custom/preview")
@_limiter.limit("10/minute")
def preview_custom_chart(
    request: Request, body: CodePreviewRequest, current_user: User = Depends(get_current_user)
):
    """
    Executes code and returns the figure JSON without saving.
    """
    import time
    from fastapi.responses import Response

    start_time = time.time()
    logger.info(f"Previewing custom chart. Code length: {len(body.code)}")
    try:
        fig = execute_custom_code(body.code)
    except BaseException as e:
        if isinstance(e, HTTPException):
            raise e

        logger.error(f"Execution failed in preview: {e}")
        # Determine error details
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.format_exception(exc_type, exc_value, exc_traceback)

        # Return as 400 Bad Request with details
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Execution Error",
                "message": str(e),
                "traceback": "".join(tb),
            },
        )

    try:
        logger.info("Serializing figure to JSON string (Plotly native)...")
        json_str = pio.to_json(fig)

        duration = time.time() - start_time
        logger.info(
            f"Serialization complete. Duration: {duration:.2f}s. Response size: {len(json_str)} bytes"
        )

        # Return directly as JSON response to avoid double serialization
        return Response(content=json_str, media_type="application/json")
    except Exception as e:
        logger.error(f"Failed to serialize figure: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Failed to serialize figure to JSON: {str(e)}"
        )


@router.post("/custom", response_model=CustomChartResponse)
def create_custom_chart(
    chart_data: CustomChartCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom chart."""
    _assert_can_create_chart(current_user)
    logger.info(f"Creating new chart with name: '{chart_data.name}'")

    # Optional: Validate code by running it once?
    # Let's render it to get the initial figure cache
    try:
        fig = execute_custom_code(chart_data.code)
        figure_json = get_clean_figure_json(fig)
    except Exception:
        figure_json = None

    # Determine next rank
    max_rank = db.query(func.max(CustomChart.rank)).scalar() or 0
    next_rank = max_rank + 1

    new_chart = CustomChart(
        name=chart_data.name,
        code=chart_data.code,
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
    db.commit()
    db.refresh(new_chart)
    logger.info(f"New chart created with ID: {new_chart.id}, Name: '{new_chart.name}'")
    return _to_custom_chart_response(new_chart)


@router.get("/custom", response_model=List[CustomChartListItemResponse])
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
    query = db.query(CustomChart).options(
        joinedload(CustomChart.creator).load_only(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
        )
    )
    if not (_is_owner(current_user) or _is_admin(current_user)):
        query = query.filter(
            or_(
                CustomChart.created_by_user_id == _user_id(current_user),
                CustomChart.public == True,
            )
        )

    # Default list is metadata-only to keep studio opening fast.
    if not include_code and not include_figure:
        query = query.options(
            load_only(
                CustomChart.id,
                CustomChart.name,
                CustomChart.category,
                CustomChart.description,
                CustomChart.tags,
                CustomChart.public,
                CustomChart.rank,
                CustomChart.created_by_user_id,
                CustomChart.created_at,
                CustomChart.updated_at,
            )
        )
    elif include_code and not include_figure:
        query = query.options(
            load_only(
                CustomChart.id,
                CustomChart.name,
                CustomChart.category,
                CustomChart.description,
                CustomChart.tags,
                CustomChart.public,
                CustomChart.rank,
                CustomChart.created_by_user_id,
                CustomChart.created_at,
                CustomChart.updated_at,
                CustomChart.code,
            )
        )
    elif include_figure and not include_code:
        query = query.options(
            load_only(
                CustomChart.id,
                CustomChart.name,
                CustomChart.category,
                CustomChart.description,
                CustomChart.tags,
                CustomChart.public,
                CustomChart.rank,
                CustomChart.created_by_user_id,
                CustomChart.created_at,
                CustomChart.updated_at,
                CustomChart.figure,
            )
        )

    charts = query.order_by(CustomChart.rank.asc(), CustomChart.created_at.desc()).all()
    return [
        _to_custom_chart_list_item(
            chart,
            include_code=include_code,
            include_figure=include_figure,
        )
        for chart in charts
    ]


@router.put("/custom/reorder")
def reorder_custom_charts(
    order_data: ReorderRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reorder custom charts based on list of IDs."""
    _assert_owner_only(current_user)

    ids = [item.id for item in order_data.items]

    # Fetch all relevant charts to update
    charts = db.query(CustomChart).filter(CustomChart.id.in_(ids)).all()
    chart_map = {str(c.id): c for c in charts}

    for index, chart_id in enumerate(ids):
        if str(chart_id) in chart_map:
            chart_map[str(chart_id)].rank = index

    db.commit()
    return {"message": "Reordered successfully"}


@router.patch("/custom/public")
def toggle_public(
    data: PublicToggle,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the public flag for one or more charts."""
    _assert_owner_only(current_user)
    db.query(CustomChart).filter(CustomChart.id.in_(data.ids)).update(
        {CustomChart.public: data.public}, synchronize_session="fetch"
    )
    db.commit()
    return {"message": f"Updated {len(data.ids)} chart(s)"}


@router.post("/custom/pdf")
def export_custom_charts_pdf(
    request: PDFExportRequest,
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

    user_identifier = str(getattr(current_user, "id", "") or "")
    pid = _start_process("Export PDF Report", user_id=user_identifier)

    try:
        if request.items:
            # Explicit list — preserve caller order
            charts = (
                db.query(CustomChart).filter(CustomChart.id.in_(request.items)).all()
            )
            chart_map = {str(c.id): c for c in charts}
            ordered_charts = [
                chart_map[cid] for cid in request.items if cid in chart_map
            ]
        else:
            # Auto-select all charts flagged for export
            ordered_charts = (
                db.query(CustomChart)
                .filter(CustomChart.public == True)
                .order_by(CustomChart.rank.asc())
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

        pdf_buffer = generate_pdf_buffer(ordered_charts, progress_cb=_on_pdf_progress, theme=request.theme)

        filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        _update_process(
            pid,
            _ProcessStatus.COMPLETED,
            "PDF Generated",
            progress=f"{total_steps}/{total_steps}",
        )

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"PDF Export failed: {e}")
        _update_process(pid, _ProcessStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom/html")
def export_custom_charts_html(
    request: PDFExportRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a standalone HTML portfolio of charts marked for export."""
    # Import task registry lazily to avoid circular-import fallback to dummy handlers.
    from ix.api.routers.task import start_process as _start_process
    from ix.api.routers.task import update_process as _update_process
    from ix.api.routers.task import ProcessStatus as _ProcessStatus

    user_identifier = str(getattr(current_user, "id", "") or "")
    pid = _start_process("Export Interactive Portfolio", user_id=user_identifier)

    try:
        chart_columns = (
            CustomChart.id,
            CustomChart.name,
            CustomChart.category,
            CustomChart.description,
            CustomChart.updated_at,
            CustomChart.figure,
        )

        if request.items:
            charts = (
                db.query(*chart_columns).filter(CustomChart.id.in_(request.items)).all()
            )
            chart_map = {str(c.id): c for c in charts}
            ordered_charts = [
                chart_map[cid] for cid in request.items if cid in chart_map
            ]
        else:
            ordered_charts = (
                db.query(*chart_columns)
                .filter(CustomChart.public.is_(True))
                .order_by(CustomChart.rank.asc())
                .all()
            )

        if not ordered_charts:
            _update_process(pid, _ProcessStatus.FAILED, "No charts found")
            raise HTTPException(status_code=404, detail="No charts marked for export")

        _update_process(pid, message="Composing HTML bundle...", progress=f"0/{len(ordered_charts)}")

        is_dark_html = request.theme.lower() == "dark"
        # Theme-dependent CSS values
        _body_bg = "#02040a" if is_dark_html else "#f8fafc"
        _body_color = "#94a3b8" if is_dark_html else "#475569"
        _header_border = "rgba(255,255,255,0.05)" if is_dark_html else "rgba(0,0,0,0.07)"
        _h1_color = "#f8fafc" if is_dark_html else "#0f172a"
        _card_bg = "rgba(255,255,255,0.02)" if is_dark_html else "#ffffff"
        _card_border = "rgba(255,255,255,0.05)" if is_dark_html else "rgba(0,0,0,0.08)"
        _card_shadow = "0 10px 30px -10px rgba(0,0,0,0.5)" if is_dark_html else "0 2px 12px -4px rgba(0,0,0,0.08)"
        _chart_hdr_bg = "rgba(0,0,0,0.2)" if is_dark_html else "#f1f5f9"
        _chart_hdr_border = "rgba(255,255,255,0.03)" if is_dark_html else "rgba(0,0,0,0.06)"
        _chart_title_color = "#e2e8f0" if is_dark_html else "#0f172a"
        # JS chart theme values
        _js_font_color = "#94a3b8" if is_dark_html else "#334155"
        _js_axis_line = "rgba(148,163,184,0.45)" if is_dark_html else "rgba(71,85,105,0.35)"
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
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
            <style>
                body {{
                    background-color: {_body_bg};
                    color: {_body_color};
                    font-family: 'Inter', sans-serif;
                    margin: 0;
                    padding: 40px 20px;
                    line-height: 1.6;
                }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                header {{ margin-bottom: 60px; border-bottom: 1px solid {_header_border}; padding-bottom: 30px; }}
                h1 {{ color: {_h1_color}; font-weight: 800; letter-spacing: -0.02em; margin: 0; }}
                .subtitle {{ font-family: 'JetBrains Mono'; font-size: 11px; text-transform: uppercase; letter-spacing: 0.2em; color: #6366f1; margin-top: 8px; }}
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
            desc = html.escape(chart.description or "Analysis pending.", quote=True).replace("\n", "<br/>")

            # Create a unique ID for Plotly div
            div_id = f"chart_{i}"

            # Apply canonical theme then compact for HTML delivery
            themed_figure = chart_theme.apply_json(chart.figure, mode=request.theme)
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
                            fig.layout.font = {{ color: '{_js_font_color}', family: 'Inter' }};
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
                                    t.textfont = Object.assign({{color: '{_js_font_color}', size: 10, family: 'Inter, sans-serif'}}, t.textfont || {{}});
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

        _update_process(pid, _ProcessStatus.COMPLETED, "Interactive Portfolio Generated")

        return Response(
            content=full_html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"HTML Export failed: {e}")
        _update_process(pid, _ProcessStatus.FAILED, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/custom/{chart_id}", response_model=CustomChartResponse)
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
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_view_chart(chart, current_user):
        raise HTTPException(status_code=404, detail="Chart not found")
    return _to_custom_chart_response(chart)


@router.post("/custom/{chart_id}/refresh", response_model=CustomChartResponse)
def refresh_custom_chart(
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Re-execute chart code and persist refreshed figure."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # Owner can refresh everything, admin can refresh all, creators can refresh their own.
    can_refresh = _is_owner(current_user) or _is_admin(current_user) or _is_chart_owner(chart, current_user)
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

    db.commit()
    db.refresh(chart)
    return _to_custom_chart_response(chart)


@router.put("/custom/{chart_id}", response_model=CustomChartResponse)
def update_custom_chart(
    chart_id: str,
    update_data: CustomChartUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a custom chart."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    old_code_len = len(chart.code) if chart.code else 0
    code_len = len(update_data.code) if update_data.code is not None else "N/A"
    logger.info(
        f"PUT /custom/{chart_id} - New Code Len: {code_len}, Old Code Len: {old_code_len}"
    )

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

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
        chart.code = update_data.code
        try:
            logger.info(f"Re-executing code for chart {chart_id}...")
            fig = execute_custom_code(update_data.code)
            figure_json = get_clean_figure_json(fig)
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
                    "message": f"Code saved but figure generation failed: {str(e)}",
                    "traceback": traceback.format_exc(),
                },
            )

    db.commit()
    db.refresh(chart)
    logger.info(
        f"Chart {chart.id} updated successfully. Figure updated: {update_data.code is not None}"
    )
    return _to_custom_chart_response(chart)


@router.delete("/custom/{chart_id}")
def delete_custom_chart(
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom chart."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db.delete(chart)
    db.commit()
    return {"message": "Chart deleted successfully"}
