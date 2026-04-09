from ix.api.routers.analytics.quant import router as quant_router
from ix.api.routers.analytics.technical import router as technical_router
from ix.api.routers.analytics.technicals import router as technicals_router
from ix.api.routers.analytics.macro import router as macro_router
from ix.api.routers.analytics.wartime import router as wartime_router
from ix.api.routers.analytics.screener import router as screener_router
from ix.api.routers.analytics.strategies import router as strategies_router
from ix.api.routers.analytics.regimes import router as regimes_router

__all__ = ["quant_router", "technical_router", "technicals_router", "macro_router", "wartime_router", "screener_router", "strategies_router", "regimes_router"]
