from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import Request
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy import or_
from typing import List, Dict, Any
from ix.db.conn import get_session
from ix.db.models import CustomChart as Chart
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from ix.misc.auth import verify_token
from ix.misc.theme import chart_theme

router = APIRouter()


class ChartMetaSchema(BaseModel):
    id: str
    name: str
    category: str | None
    description: str | None
    updated_at: datetime | None
    rank: int = 0
    public: bool = True
    created_by_user_id: str | None = None
    created_by_email: str | None = None
    created_by_name: str | None = None
    code: str | None = None
    figure: Any | None = None  # Added figure data to bundle with summary
    chart_style: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    categories: List[str]
    charts_by_category: Dict[str, List[ChartMetaSchema]]


from ix.db.models.user import User


def _theme_figure_for_delivery(figure: Any) -> Any:
    """Apply canonical misc theme at response-time without mutating DB payload."""
    if figure is None:
        return None
    return chart_theme.apply_json(figure, mode="light")


def _get_optional_user(request: Request) -> User | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    user = User.get_by_email(email)
    if not user or getattr(user, "disabled", False):
        return None
    return user


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
    include_figures: bool = False,
    include_code: bool = False,
):
    """
    Returns a summary of all categories and chart metadata.
    Figure/code payloads are excluded by default to reduce response size and RAM usage.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    current_user = _get_optional_user(request)
    is_admin = bool(current_user and current_user.effective_role in User.ADMIN_ROLES)
    current_uid = str(getattr(current_user, "id", "") or "") if current_user else None
    include_code_for_user = bool(include_code and is_admin)

    chart_columns = [
        Chart.id,
        Chart.name,
        Chart.category,
        Chart.description,
        Chart.updated_at,
        Chart.rank,
        Chart.public,
        Chart.created_by_user_id,
        Chart.chart_style,
    ]
    if include_figures:
        chart_columns.append(Chart.figure)
    if include_code_for_user:
        chart_columns.append(Chart.code)

    query = db.query(Chart).options(
        load_only(*chart_columns),
        joinedload(Chart.creator).load_only(
            User.id,
            User.email,
            User.first_name,
            User.last_name,
        ),
    )

    if not is_admin:
        if current_uid:
            query = query.filter(
                or_(
                    Chart.public == True,
                    Chart.created_by_user_id == current_uid,
                )
            )
        else:
            query = query.filter(Chart.public == True)

    charts = query.all()

    summary = {"categories": [], "charts_by_category": {}}
    categories_set = set()

    # Process charts and build summary
    for chart in charts:
        cat = chart.category or "Uncategorized"
        if cat not in summary["charts_by_category"]:
            summary["charts_by_category"][cat] = []
            categories_set.add(cat)

        creator = getattr(chart, "creator", None)
        creator_id = getattr(chart, "created_by_user_id", None)
        creator_email = getattr(creator, "email", None) if creator else None
        creator_name = " ".join(
            [x for x in [getattr(creator, "first_name", None), getattr(creator, "last_name", None)] if x]
        ) or None
        meta = ChartMetaSchema(
            id=str(chart.id),
            name=chart.name or "Untitled",
            category=chart.category,
            description=chart.description,
            updated_at=chart.updated_at,
            rank=int(chart.rank or 0),
            public=bool(chart.public),
            created_by_user_id=str(creator_id) if creator_id else None,
            created_by_email=str(creator_email) if creator_email else None,
            created_by_name=creator_name,
            code=chart.code if include_code_for_user else None,
            figure=_theme_figure_for_delivery(chart.figure) if include_figures else None,
            chart_style=chart.chart_style,
        )

        summary["charts_by_category"][cat].append(meta)

    summary["categories"] = sorted(list(categories_set))

    for cat in summary["charts_by_category"]:
        summary["charts_by_category"][cat].sort(key=lambda x: (x.rank, x.name))

    return summary


@router.get("/dashboard/charts/{chart_id}/figure")
def get_chart_figure(
    chart_id: str, request: Request, response: Response, db: Session = Depends(get_session)
):
    """
    Returns the Plotly JSON figure for a specific custom chart.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    chart_fields = [
        Chart.id,
        Chart.name,
        Chart.figure,
        Chart.chart_style,
        Chart.public,
        Chart.created_by_user_id,
    ]
    chart = db.query(Chart).options(load_only(*chart_fields)).filter(Chart.id == chart_id).first()
    if not chart:
        # Try finding by name if ID fails (less preferred but helps migration)
        chart = db.query(Chart).options(load_only(*chart_fields)).filter(Chart.name == chart_id).first()
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found")

    current_user = _get_optional_user(request)
    is_admin = bool(current_user and current_user.effective_role in User.ADMIN_ROLES)
    current_uid = str(getattr(current_user, "id", "") or "") if current_user else ""
    is_owner_chart = bool(current_uid and str(getattr(chart, "created_by_user_id", "") or "") == current_uid)
    if not is_admin and not bool(chart.public) and not is_owner_chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    if not chart.figure:
        # For CustomCharts, we might need to re-execute the code if figure is missing
        # But we assume the studio saves the figure.
        raise HTTPException(
            status_code=404, detail="Figure data missing for this chart"
        )

    return {
        "figure": _theme_figure_for_delivery(chart.figure),
        "chart_style": chart.chart_style,
    }
