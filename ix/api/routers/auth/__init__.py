from ix.api.routers.auth.auth import router as auth_router
from ix.api.routers.auth.admin import router as admin_router
from ix.api.routers.auth.user import router as user_router
from ix.api.routers.auth.api_keys import router as api_keys_router

__all__ = ["auth_router", "admin_router", "user_router", "api_keys_router"]
