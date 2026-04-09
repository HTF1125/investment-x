from ix.api.routers.data.timeseries import router as timeseries_router
from ix.api.routers.data.series import router as series_router
from ix.api.routers.data.evaluation import router as evaluation_router
from ix.api.routers.data.collectors import router as collectors_router
from ix.api.routers.data.sources import router as sources_router
from ix.api.routers.data.credit_watchlist import router as credit_watchlist_router

__all__ = [
    "timeseries_router",
    "series_router",
    "evaluation_router",
    "collectors_router",
    "sources_router",
    "credit_watchlist_router",
]
