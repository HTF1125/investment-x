from ix.api.routers.charts.custom import router as custom_router
from ix.api.routers.charts.chart_packs import router as chart_packs_router
from ix.api.routers.charts.chart_workspaces import router as chart_workspaces_router
from ix.api.routers.charts.whiteboard import router as whiteboard_router
from ix.api.routers.charts.dashboard import router as dashboard_router

__all__ = [
    "custom_router",
    "chart_packs_router",
    "chart_workspaces_router",
    "whiteboard_router",
    "dashboard_router",
]
