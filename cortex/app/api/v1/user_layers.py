"""
User Layers API

Endpoints for users to discover their accessible Knowledge Layers and quotas.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.keycloak import verifier
from app.services.security.layer_manager import layer_manager
from app.models.layer import LayerResponse

router = APIRouter(prefix="/layers", tags=["Layers"])

@router.get(
    "/",
    response_model=List[LayerResponse]
)
async def get_my_layers(
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verifier.verify_token)
) -> List[LayerResponse]:
    """
    List all knowledge layers accessible to the current user.
    """
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    layers = await layer_manager.resolve_layers_for_user(
        user_roles=roles,
        db=db
    )

    return [LayerResponse.model_validate(l) for l in layers]

@router.get(
    "/me",
    response_model=LayerResponse
)
async def get_my_private_layer(
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verifier.verify_token)
) -> LayerResponse:
    """
    Get the current user's private layer details (including quota).
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID (sub) not found in token"
        )

    username = payload.get("preferred_username", "unknown")

    # Get or Create
    # We use create_private_layer_for_user which handles "get existing" inside
    layer = await layer_manager.create_private_layer_for_user(
        user_id=user_id,
        username=username,
        db=db
    )

    return LayerResponse.model_validate(layer)
