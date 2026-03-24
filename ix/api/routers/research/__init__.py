from ix.api.routers.research.news import router as news_router
from ix.api.routers.research.insights import router as insights_router
from ix.api.routers.research.scorecards import router as scorecards_router
from ix.api.routers.research.tts import router as tts_router
from ix.api.routers.research.library import router as library_router

__all__ = ["news_router", "insights_router", "scorecards_router", "tts_router", "library_router"]
