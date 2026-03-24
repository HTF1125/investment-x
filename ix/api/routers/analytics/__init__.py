from ix.api.routers.analytics.quant import router as quant_router
from ix.api.routers.analytics.technical import router as technical_router
from ix.api.routers.analytics.macro import router as macro_router
from ix.api.routers.analytics.wartime import router as wartime_router
from ix.api.routers.analytics.screener import router as screener_router

__all__ = ["quant_router", "technical_router", "macro_router", "wartime_router", "screener_router"]
