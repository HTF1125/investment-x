from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ix.db.conn import get_session
from ix.db.models import CustomChart as Chart
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter()


class ChartMetaSchema(BaseModel):
    id: str
    name: str
    category: str | None
    description: str | None
    updated_at: datetime | None
    rank: int = 0
    export_pdf: bool = True
    code: str | None = None
    figure: Any | None = None  # Added figure data to bundle with summary

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    categories: List[str]
    charts_by_category: Dict[str, List[ChartMetaSchema]]


from ix.api.dependencies import get_current_user
from ix.db.models.user import User


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    response: Response,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    include_figures: bool = True,  # Default to true for fast dashboard load
):
    """
    Returns a summary of all categories and chart metadata.
    Includes figure data by default to prevent client-side fetching waterfalls.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    query = db.query(Chart)

    if not current_user.is_admin:
        query = query.filter(Chart.export_pdf == True)

    charts = query.all()

    summary = {"categories": [], "charts_by_category": {}}
    categories_set = set()

    # Process charts and build summary
    for chart in charts:
        cat = chart.category or "Uncategorized"
        if cat not in summary["charts_by_category"]:
            summary["charts_by_category"][cat] = []
            categories_set.add(cat)

        meta = ChartMetaSchema.from_orm(chart)

        # Security: Never leak logic to non-admins
        if not current_user.is_admin:
            meta.code = None

        # Include figure for all charts
        if include_figures:
            meta.figure = chart.figure

        summary["charts_by_category"][cat].append(meta)

    summary["categories"] = sorted(list(categories_set))

    for cat in summary["charts_by_category"]:
        summary["charts_by_category"][cat].sort(key=lambda x: (x.rank, x.name))

    return summary


@router.get("/dashboard/charts/{chart_id}/figure")
def get_chart_figure(
    chart_id: str, response: Response, db: Session = Depends(get_session)
):
    """
    Returns the Plotly JSON figure for a specific custom chart.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    chart = db.query(Chart).filter(Chart.id == chart_id).first()
    if not chart:
        # Try finding by name if ID fails (less preferred but helps migration)
        chart = db.query(Chart).filter(Chart.name == chart_id).first()
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found")

    if not chart.figure:
        # For CustomCharts, we might need to re-execute the code if figure is missing
        # But we assume the studio saves the figure.
        raise HTTPException(
            status_code=404, detail="Figure data missing for this chart"
        )

    return chart.figure
