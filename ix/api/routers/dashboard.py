from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, load_only
from typing import List, Dict, Any
from ix.db.conn import get_session
from ix.db.models import Chart
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class ChartMetaSchema(BaseModel):
    code: str
    category: str | None
    description: str | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    categories: List[str]
    charts_by_category: Dict[str, List[ChartMetaSchema]]


from ix.api.dependencies import get_current_user
from ix.db.models.user import User


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_session)):
    """
    Returns a summary of all categories and chart metadata for the gallery.
    """
    charts = (
        db.query(Chart)
        .options(
            load_only(Chart.code, Chart.category, Chart.description, Chart.updated_at)
        )
        .all()
    )

    summary = {"categories": [], "charts_by_category": {}}

    categories_set = set()

    for chart in charts:
        cat = chart.category or "Uncategorized"
        if cat not in summary["charts_by_category"]:
            summary["charts_by_category"][cat] = []
            categories_set.add(cat)

        summary["charts_by_category"][cat].append(ChartMetaSchema.from_orm(chart))

    # Sort categories alphabetically
    summary["categories"] = sorted(list(categories_set))

    # Sort charts within categories by code
    for cat in summary["charts_by_category"]:
        summary["charts_by_category"][cat].sort(key=lambda x: x.code)

    return summary


@router.get("/dashboard/charts/{code}/figure")
def get_chart_figure(code: str, db: Session = Depends(get_session)):
    """
    Returns the Plotly JSON figure for a specific chart.
    """
    chart = db.query(Chart).filter(Chart.code == code).first()
    if not chart:
        # Fallback: maybe it's the name?
        chart = (
            db.query(Chart).filter(Chart.category == code).first()
        )  # Unexpected but just in case
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found")

    if not chart.figure:
        try:
            chart.update_figure()
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to render chart: {e}")

    return chart.figure
