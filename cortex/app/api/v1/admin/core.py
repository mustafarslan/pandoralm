"""
Admin Endpoints
Protected endpoints requiring admin or vector-ops roles
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import UserContext, require_auth
from app.core.rbac import Permission
from app.services.graphrag import get_graph_store
from app.services import get_vector_store

router = APIRouter()


# ========================================
# Response Models
# ========================================

class UserInfoResponse(BaseModel):
    """Current user information."""
    sub: str
    email: str
    username: str
    name: str
    roles: List[str]
    groups: List[str]
    is_admin: bool
    is_vector_ops: bool


class SystemStatsResponse(BaseModel):
    """System-wide statistics."""
    vector_stats: dict
    graph_connected: bool
    workspaces: List[str]


# ========================================
# User Info Endpoints
# ========================================

@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    user: UserContext = Depends(require_auth),
) -> UserInfoResponse:
    """Get current authenticated user information."""
    return UserInfoResponse(
        sub=user.sub,
        email=user.email,
        username=user.username,
        name=user.name,
        roles=user.roles,
        groups=user.groups,
        is_admin=user.is_admin(),
        is_vector_ops=user.is_vector_ops(),
    )


@router.get("/permissions")
async def check_permissions(
    user: UserContext = Depends(require_auth),
) -> dict:
    """Check user's permissions."""
    return {
        "user_id": user.sub,
        "permissions": {
            "can_read": True,
            "can_write": user.has_any_role(["user", "admin", "vector-ops"]),
            "can_admin": user.is_admin(),
            "can_vector_ops": user.is_vector_ops(),
        },
        "roles": user.roles,
        "groups": user.groups,
    }


# ========================================
# Admin-Only Endpoints
# ========================================

@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    dependencies=[Depends(Permission.admin())],
)
async def get_system_stats() -> SystemStatsResponse:
    """Get system-wide statistics. Admin only."""
    vector_store = get_vector_store()
    graph_store = get_graph_store()

    vector_stats = vector_store.get_total_stats()
    collections = vector_store.list_collections()

    return SystemStatsResponse(
        vector_stats=vector_stats,
        graph_connected=graph_store.verify_connectivity(),
        workspaces=[c["workspace_id"] for c in collections],
    )


@router.post(
    "/clear-workspace/{workspace_id}",
    dependencies=[Depends(Permission.admin())],
)
async def clear_workspace_data(workspace_id: str) -> dict:
    """
    Clear all data for a workspace. Admin only.

    WARNING: This permanently deletes vectors and graph data.
    """
    vector_store = get_vector_store()
    graph_store = get_graph_store()

    # Delete vectors
    vector_deleted = vector_store.delete_collection(workspace_id)

    # Delete graph
    try:
        graph_store.clear_workspace(workspace_id)
        graph_deleted = True
    except Exception:
        graph_deleted = False

    return {
        "workspace_id": workspace_id,
        "vectors_deleted": vector_deleted,
        "graph_deleted": graph_deleted,
    }


# ========================================
# Vector Ops Endpoints
# ========================================

@router.get(
    "/vector-ops/collections",
    dependencies=[Depends(Permission.vector_ops())],
)
async def list_all_collections() -> dict:
    """List all vector collections. Vector-ops only."""
    vector_store = get_vector_store()
    return {
        "collections": vector_store.list_collections(),
        "total_stats": vector_store.get_total_stats(),
    }


@router.delete(
    "/vector-ops/collections/{workspace_id}",
    dependencies=[Depends(Permission.vector_ops())],
)
async def delete_collection(workspace_id: str) -> dict:
    """Delete a vector collection. Vector-ops only."""
    vector_store = get_vector_store()

    success = vector_store.delete_collection(workspace_id)

    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {"deleted": workspace_id, "status": "deleted"}


@router.post(
    "/vector-ops/reindex-all",
    dependencies=[Depends(Permission.vector_ops())],
)
async def reindex_all_workspaces() -> dict:
    """
    Trigger reindexing for all workspaces. Vector-ops only.

    This queues background jobs for each workspace.
    """
    from app.workers.tasks.indexing import reindex_vectors

    vector_store = get_vector_store()
    collections = vector_store.list_collections()

    jobs = []
    for coll in collections:
        try:
            result = reindex_vectors.delay(coll["workspace_id"])
            jobs.append({
                "workspace_id": coll["workspace_id"],
                "job_id": result.id,
            })
        except Exception as e:
            jobs.append({
                "workspace_id": coll["workspace_id"],
                "error": str(e),
            })

    return {
        "status": "queued",
        "jobs": jobs,
        "total": len(jobs),
    }


# ========================================
# System Preferences (Frontend Compat)
# ========================================

@router.get("/system-preferences")
async def get_system_preferences() -> dict:
    """
    Get system preferences for Frontend Settings page.
    Maps environment variables to the format expected by AnythingLLM frontend.
    """
    from app.core.config import settings

    return {
        "settings": {
            "MultiUserMode": True,
            "AuthToken": settings.OPENAI_API_KEY,
            # Keycloak / Identity
            "KeycloakRealm": settings.KEYCLOAK_REALM,
            "KeycloakURL": settings.KEYCLOAK_PUBLIC_URL,
            "KeycloakClientId": settings.KEYCLOAK_CLIENT_ID,
            # Placeholder for Role Mapping (not yet configurable via Env)
            "RoleMapping": [],
            # Other common settings
            "VectorDB": "lancedb",
            "EmbeddingEngine": settings.LLM_PROVIDER,
        }
    }

@router.get("/system-preferences-for")
async def get_system_preferences_filtered(labels: str = Query(default="")) -> dict:
    """
    Get specific system preferences.
    Returns the full set for now, as frontend usually handles filtering.
    """
    return await get_system_preferences()
