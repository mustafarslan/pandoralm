"""
Admin API Package
Combines core admin endpoints and layer management.
"""
from fastapi import APIRouter

# Import routers from submodules
from app.api.v1.admin.core import router as core_router
from app.api.v1.admin.layers import router as layers_router

# Create combined router for backwards compatibility
router = APIRouter()

# Include core admin routes (user info, stats, vector ops)
router.include_router(core_router)

# Include layer management routes (already has /admin/layers prefix)
# layers_router has its own prefix, so we include it separately

__all__ = ["router", "layers_router"]
