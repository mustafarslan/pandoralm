"""
Workspace Layer Management API
Manage knowledge layer subscriptions for workspaces.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.keycloak import verifier
from app.models.layer import LayerType
from app.services.workspace_layer_service import get_workspace_layer_service, WorkspaceLayerService
from app.api.v1.admin.layers import LayerResponse

router = APIRouter()

@router.get("/{workspace_id}/layers", response_model=List[LayerResponse])
async def get_workspace_layers(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    service: WorkspaceLayerService = Depends(get_workspace_layer_service),
    token_payload: dict = Depends(verifier.verify_token)
):
    """
    Get all knowledge layers accessible to this workspace.

    This includes:
    1. Global System Layers (subscribed)
    2. Global Organization Layers (subscribed)
    3. Private User Layers (if user owns them & they are mapped)
    4. Team/Project Layers (subscribed)
    """
    layers = await service.get_workspace_layers(workspace_id, db)
    return [layer.to_dict() for layer in layers]


@router.post("/{workspace_id}/layers/{layer_id}")
async def map_layer_to_workspace(
    workspace_id: str,
    layer_id: UUID,
    access_mode: str = Body("read", embed=True),
    db: AsyncSession = Depends(get_db),
    service: WorkspaceLayerService = Depends(get_workspace_layer_service),
    token_payload: dict = Depends(verifier.verify_token)
):
    """
    Map a knowledge layer to a workspace.

    - 'access_mode': 'read' or 'write'
    - Requires ADMIN role or Layer Owner.
    """
    # TODO: Strict RBAC check here (e.g. check if user is admin or layer owner)

    # Check if access_mode is valid
    if access_mode not in ["read", "write"]:
        raise HTTPException(status_code=400, detail="access_mode must be 'read' or 'write'")

    mapping = await service.add_layer_to_workspace(workspace_id, layer_id, access_mode, db)
    return {
        "status": "success",
        "message": f"Mapped Layer {layer_id} to Workspace {workspace_id} ({access_mode})",
        "permission": mapping.access_mode
    }


@router.delete("/{workspace_id}/layers/{layer_id}")
async def unmap_layer_from_workspace(
    workspace_id: str,
    layer_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: WorkspaceLayerService = Depends(get_workspace_layer_service),
    token_payload: dict = Depends(verifier.verify_token)
):
    """
    Remove a layer from a workspace.
    """
    # TODO: Strict RBAC check here

    deleted = await service.remove_layer_from_workspace(workspace_id, layer_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")

    return {"status": "success", "message": "Layer removed from workspace"}


@router.post("/{workspace_id}/initialize")
async def initialize_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    service: WorkspaceLayerService = Depends(get_workspace_layer_service),
    token_payload: dict = Depends(verifier.verify_token)
):
    """
    Initialize default layers for a new workspace.
    Call this when a workspace is created.
    """
    user_id = token_payload.get("sub")
    username = token_payload.get("preferred_username", "unknown")

    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")

    mappings = await service.initialize_workspace_layers(workspace_id, user_id, username, db)

    return {
        "status": "success",
        "message": f"Initialized {len(mappings)} layers for workspace {workspace_id}",
        "layers": [str(m.layer_id) for m in mappings]
    }
