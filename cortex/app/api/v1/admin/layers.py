"""
Admin Layer Management API

Protected endpoints requiring super_admin role for layer CRUD operations.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.keycloak import verifier
from app.services.security.layer_manager import layer_manager
from app.services.vector_store import get_vector_store
from app.models.layer import (
    Layer,
    LayerPermission,
    AccessLevel,
    LayerCreate,
    LayerResponse,
    PermissionCreate,
    PermissionResponse,
    QuotaUpdate,
    BulkQuotaUpdate,
)

router = APIRouter(prefix="/admin/layers", tags=["Admin - Layers"])


# ========================================
# Security Dependencies
# ========================================

async def require_super_admin(
    payload: dict = Depends(verifier.verify_token)
) -> dict:
    """
    Dependency: Requires 'admin' realm role.

    Raises:
        HTTPException: 403 if user lacks admin role
    """
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required. Missing 'admin' role."
        )
    return payload


# ========================================
# Layer CRUD Endpoints
# ========================================

@router.post(
    "/",
    response_model=LayerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)]
)
async def create_layer(
    data: LayerCreate,
    db: AsyncSession = Depends(get_db)
) -> LayerResponse:
    """
    Create a new Knowledge Layer.

    Requires super_admin role.
    """
    try:
        layer = await layer_manager.create_layer(data, db)
        return LayerResponse.model_validate(layer)
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Layer with name '{data.name}' already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=List[dict],
    dependencies=[Depends(require_super_admin)]
)
async def list_layers(
    db: AsyncSession = Depends(get_db),
    include_vector_counts: bool = False
) -> List[dict]:
    """
    List all Knowledge Layers.

    Optionally includes vector count per layer from LanceDB.
    Requires super_admin role.
    """
    layers = await layer_manager.list_layers(db)

    layer_stats = {}
    if include_vector_counts:
        try:
            vector_store = get_vector_store()
            layer_stats = vector_store.get_layer_distribution()
        except Exception:
            pass

    result = []
    for layer in layers:
        layer_dict = layer.to_dict()
        layer_dict["permissions"] = [p.to_dict() for p in layer.permissions]

        # Optional: Aggregate vector counts
        if include_vector_counts:
            # Match UUID string to stats key
            layer_dict["vector_count"] = layer_stats.get(str(layer.id), 0)

        result.append(layer_dict)

    return result


@router.get(
    "/{layer_id}",
    response_model=dict,
    dependencies=[Depends(require_super_admin)]
)
async def get_layer(
    layer_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get a specific layer by ID.

    Requires super_admin role.
    """
    layer = await layer_manager.get_layer(layer_id, db)

    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer {layer_id} not found"
        )

    layer_dict = layer.to_dict()
    layer_dict["permissions"] = [p.to_dict() for p in layer.permissions]
    return layer_dict


# ========================================
# Permission Management Endpoints
# ========================================

@router.post(
    "/{layer_id}/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)]
)
async def add_permission(
    layer_id: UUID,
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db)
) -> PermissionResponse:
    """
    Add a permission to a layer.

    Maps a Keycloak role pattern to layer access.

    Role pattern examples:
    - "group:engineering" - exact match
    - "group:*" - wildcard (matches group:anything)

    Requires super_admin role.
    """
    # Verify layer exists
    layer = await layer_manager.get_layer(layer_id, db)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer {layer_id} not found"
        )

    perm = await layer_manager.assign_permission(
        layer_id=layer_id,
        role=data.role_pattern,
        level=data.access_level,
        db=db
    )

    return PermissionResponse.model_validate(perm)


@router.delete(
    "/{layer_id}/permissions/{perm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_super_admin)]
)
async def revoke_permission(
    layer_id: UUID,
    perm_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Revoke a permission from a layer.

    Requires super_admin role.
    """
    revoked = await layer_manager.revoke_permission(perm_id, db)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission {perm_id} not found"
        )


# ========================================
# Quota Management Endpoints
# ========================================

@router.put(
    "/{layer_id}/quota",
    response_model=LayerResponse,
    dependencies=[Depends(require_super_admin)]
)
async def update_layer_quota(
    layer_id: UUID,
    data: QuotaUpdate,
    db: AsyncSession = Depends(get_db)
) -> LayerResponse:
    """
    Update storage quota for a specific layer.
    """
    layer = await layer_manager.update_layer_quota(layer_id, data, db)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer {layer_id} not found"
        )
    return LayerResponse.model_validate(layer)


@router.put(
    "/quotas/bulk",
    response_model=dict,
    dependencies=[Depends(require_super_admin)]
)
async def bulk_update_quotas(
    data: BulkQuotaUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Bulk update quotas for all layers of a specific type.
    """
    count = await layer_manager.bulk_update_quotas(data, db)
    return {"updated_count": count, "message": f"Updated {count} layers"}


@router.get(
    "/users/{user_id}/quota",
    response_model=LayerResponse,
    dependencies=[Depends(require_super_admin)]
)
async def get_user_quota(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> LayerResponse:
    """
    Get quota for a user's private layer.
    """
    layer = await layer_manager.get_user_private_layer(user_id, db)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Private layer for user {user_id} not found"
        )
    return LayerResponse.model_validate(layer)


@router.put(
    "/users/{user_id}/quota",
    response_model=LayerResponse,
    dependencies=[Depends(require_super_admin)]
)
async def update_user_quota(
    user_id: str,
    data: QuotaUpdate,
    db: AsyncSession = Depends(get_db)
) -> LayerResponse:
    """
    Update quota for a user's private layer.
    """
    layer = await layer_manager.get_user_private_layer(user_id, db)
    if not layer:
        # Auto-create if not exists? Or 404?
        # Typically admin wants to set quota, so maybe auto-create or error.
        # Given "User Lifecycle", it should exist on creation/login.
        # I'll return 404 to be safe.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Private layer for user {user_id} not found"
        )

    # We call update_layer_quota with the found ID
    updated = await layer_manager.update_layer_quota(UUID(layer.id), data, db)
    return LayerResponse.model_validate(updated)


# ========================================
# Lifecycle Management Endpoints
# ========================================

@router.post(
    "/cleanup",
    response_model=dict,
    dependencies=[Depends(require_super_admin)]
)
async def cleanup_soft_deleted_layers(
    retention_days: int = 30,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Manually trigger cleanup of soft-deleted layers older than retention period.
    """
    count = await layer_manager.cleanup_soft_deleted_layers(db, retention_days)
    return {"deleted_count": count, "message": f"Permanently deleted {count} layers"}

