from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.io as pio
import json
import traceback
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import utils
import textwrap

from ix.db.conn import get_session
from ix.db.models import CustomChart, User
from ix.api.dependencies import get_current_user
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()

# --- Pydantic Models ---


class CustomChartCreate(BaseModel):
    name: str = "Untitled Analysis"
    code: str
    category: Optional[str] = "Personal"
    description: Optional[str] = None
    tags: List[str] = []


class CustomChartUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CustomChartResponse(BaseModel):
    id: str
    name: Optional[str]
    code: str
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    figure: Optional[Dict[str, Any]]
    rank: int = 0
    created_at: datetime
    updated_at: datetime

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


# --- Helper Functions ---


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
    local_scope = {}

    # Pre-import common libraries used in Investment-X charts
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from ix.db.query import Series, MultiSeries, MonthEndOffset

    # Try to import style helpers if available
    try:
        from ix.cht.style import get_value_label, get_color, apply_academic_style
    except ImportError:
        # Fallback mocks if not found (though they should be there)
        def get_value_label(s, n, f):
            return n

        def get_color(n, i):
            return None

        def apply_academic_style(f):
            pass

    global_scope = {
        "pd": pd,
        "px": px,
        "go": go,
        "make_subplots": make_subplots,
        "Series": Series,
        "MultiSeries": MultiSeries,
        "MonthEndOffset": MonthEndOffset,
        "get_value_label": get_value_label,
        "get_color": get_color,
        "apply_academic_style": apply_academic_style,
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
        exec(code, global_scope)

        # 5. Extract Figure from the modified scope
        if "fig" in global_scope:
            return global_scope["fig"]

        # If the code was an expression that evaluated to a fig (hard with exec)
        # We assume users will assign to 'fig' as per standard convention
        raise ValueError(
            "The code must define a variable named 'fig' containing the Plotly figure."
        )

    except Exception as e:
        logger.error(f"Error executing custom chart code: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Execution Error: {str(e)}")


def generate_pdf_buffer(charts: List[CustomChart]) -> BytesIO:
    buffer = BytesIO()
    # Use landscape for charts usually
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    for chart in charts:
        # Validate chart has figure
        if not chart.figure:
            continue

        try:
            # 1. Render title
            c.setFont("Helvetica-Bold", 18)
            title = chart.name or "Untitled Analysis"
            c.drawString(50, height - 50, title)

            # 2. Render meta
            c.setFont("Helvetica", 10)
            meta = f"Category: {chart.category} | Updated: {chart.updated_at.strftime('%Y-%m-%d')}"
            c.drawString(50, height - 70, meta)

            # 3. Render description (wrapped)
            if chart.description:
                c.setFont("Helvetica-Oblique", 10)
                desc_lines = textwrap.wrap(chart.description, width=120)
                y_desc = height - 90
                for line in desc_lines[:3]:  # Limit lines
                    c.drawString(50, y_desc, line)
                    y_desc -= 12

            # 4. Render Chart Image
            # Reconstruct figure from JSON
            fig = pio.from_json(json.dumps(chart.figure))

            # Convert to image bytes
            # Note: Using default engine (usually kaleido if installed)
            img_bytes = fig.to_image(format="png", width=1000, height=550, scale=2)

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

            c.showPage()

        except Exception as e:
            logger.error(f"Failed to render chart {chart.id} to PDF: {e}")
            c.setFont("Helvetica", 12)
            c.drawString(50, height / 2, f"Error rendering chart: {str(e)}")
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# --- Endpoints ---


@router.post("/custom/preview")
def preview_custom_chart(
    request: CodePreviewRequest, current_user: User = Depends(get_current_user)
):
    """
    Executes code and returns the figure JSON without saving.
    """
    fig = execute_custom_code(request.code)
    try:
        return json.loads(pio.to_json(fig))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to serialize figure to JSON."
        )


@router.post("/custom", response_model=CustomChartResponse)
def create_custom_chart(
    chart_data: CustomChartCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom chart."""

    # Optional: Validate code by running it once?
    # Let's render it to get the initial figure cache
    try:
        fig = execute_custom_code(chart_data.code)
        figure_json = json.loads(pio.to_json(fig))
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
        rank=next_rank,
    )

    db.add(new_chart)
    db.commit()
    db.refresh(new_chart)
    return new_chart


@router.get("/custom", response_model=List[CustomChartResponse])
def list_custom_charts(
    db: Session = Depends(get_session), current_user: User = Depends(get_current_user)
):
    """List all custom charts (shared across admins)."""
    return (
        db.query(CustomChart)
        .order_by(CustomChart.rank.asc(), CustomChart.created_at.desc())
        .all()
    )


@router.put("/custom/reorder")
def reorder_custom_charts(
    order_data: ReorderRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reorder custom charts based on list of IDs."""

    ids = [item.id for item in order_data.items]

    # Fetch all relevant charts to update
    charts = db.query(CustomChart).filter(CustomChart.id.in_(ids)).all()
    chart_map = {str(c.id): c for c in charts}

    for index, chart_id in enumerate(ids):
        if str(chart_id) in chart_map:
            chart_map[str(chart_id)].rank = index

    db.commit()
    return {"message": "Reordered successfully"}


@router.post("/custom/pdf")
def export_custom_charts_pdf(
    request: PDFExportRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a PDF of the requested charts in order."""

    # Fetch charts
    # We want to preserve order from request.items
    charts = db.query(CustomChart).filter(CustomChart.id.in_(request.items)).all()
    chart_map = {str(c.id): c for c in charts}

    ordered_charts = []
    for cid in request.items:
        if cid in chart_map:
            ordered_charts.append(chart_map[cid])

    if not ordered_charts:
        raise HTTPException(status_code=404, detail="No charts found to export")

    pdf_buffer = generate_pdf_buffer(ordered_charts)

    filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/custom/{chart_id}", response_model=CustomChartResponse)
def get_custom_chart(
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a specific custom chart."""
    chart = db.query(CustomChart).filter(CustomChart.id == chart_id).first()

    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart


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

    # Update fields if provided
    if update_data.name is not None:
        chart.name = update_data.name
    if update_data.category is not None:
        chart.category = update_data.category
    if update_data.description is not None:
        chart.description = update_data.description
    if update_data.tags is not None:
        chart.tags = update_data.tags

    # If code changes, re-render
    if update_data.code is not None:
        chart.code = update_data.code
        try:
            fig = execute_custom_code(update_data.code)
            chart.figure = json.loads(pio.to_json(fig))
        except Exception:
            pass

    db.commit()
    db.refresh(chart)
    return chart


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

    db.delete(chart)
    db.commit()
    return {"message": "Chart deleted successfully"}
