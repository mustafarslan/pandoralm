"""
Auth API Endpoints

Endpoints for layer resolution and user auth state.
"""
from typing import List
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.keycloak import verifier
from app.services.security.layer_manager import layer_manager
from app.models.layer import LayerType

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LayerInfo(BaseModel):
    """Layer information for frontend."""
    id: str
    name: str
    type: str
    color: str
    permissions: List[str]


class UserLayersResponse(BaseModel):
    """Response for user's accessible layers."""
    layers: List[LayerInfo]


@router.get("/layers", response_model=UserLayersResponse)
async def resolve_user_layers(
    payload: dict = Depends(verifier.verify_token),
    db: AsyncSession = Depends(get_db)
) -> UserLayersResponse:
    """
    Resolve the Knowledge Layers accessible to the current user
    based on their Keycloak roles.

    This is the primary endpoint for frontend to fetch accessible layers
    at application boot.
    """
    # Extract realm_access.roles from JWT
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    # Resolve layers from database
    layers = await layer_manager.resolve_layers_for_user(roles, db)

    # Transform to response format
    layer_infos = []
    for layer in layers:
        # Collect permissions for this layer
        perms = []
        for p in layer.permissions:
            if p.role_pattern in roles or p.role_pattern == "*":
                perms.append(p.access_level.value)

        layer_infos.append(LayerInfo(
            id=layer.id,
            name=layer.name,
            type=layer.type.value,
            color=layer.color,
            permissions=list(set(perms)) if perms else ["READ"]
        ))

    return UserLayersResponse(layers=layer_infos)


@router.get("/me")
async def get_current_user(
    payload: dict = Depends(verifier.verify_token)
) -> dict:
    """
    Get current user information from JWT.
    """
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "preferred_username": payload.get("preferred_username"),
        "name": payload.get("name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
        "groups": payload.get("groups", []),
    }


# === SSO Endpoints ===

from fastapi.responses import RedirectResponse
from app.core.config import settings


@router.get("/sso/{provider}")
async def sso_redirect(provider: str) -> RedirectResponse:
    """
    Redirect to SSO provider (Keycloak OIDC or SAML).

    Supported providers: 'oidc', 'saml'
    """
    # Use public URL for browser redirects (not Docker internal hostname)
    base_url = getattr(settings, 'KEYCLOAK_PUBLIC_URL', settings.KEYCLOAK_URL).rstrip("/")
    realm = settings.KEYCLOAK_REALM
    client_id = settings.KEYCLOAK_CLIENT_ID

    # Determine redirect URI (where Keycloak sends user after auth)
    # Hardcode localhost:3002 for local development
    redirect_uri = "http://localhost:3002/auth/callback"

    if provider == "oidc":
        # Standard OIDC Authorization Code Flow
        auth_url = (
            f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&scope=openid profile email"
            f"&redirect_uri={redirect_uri}"
        )
        return RedirectResponse(url=auth_url, status_code=302)

    elif provider == "saml":
        # SAML SSO Redirect
        # Keycloak SAML endpoint
        saml_url = (
            f"{base_url}/realms/{realm}/protocol/saml"
            f"?SAMLRequest=<placeholder>"  # SAML request would be generated here
            f"&RelayState={redirect_uri}"
        )
        # For production, use python-saml2 to generate proper SAML request
        # For now, redirect to OIDC as fallback (SAML requires more setup)
        return RedirectResponse(
            url=f"{base_url}/realms/{realm}/protocol/openid-connect/auth"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&scope=openid profile email"
            f"&redirect_uri={redirect_uri}",
            status_code=302
        )

    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown SSO provider: {provider}")


@router.get("/callback")
async def sso_callback(code: str, state: str = None) -> dict:
    """
    Handle SSO callback from Keycloak.

    Exchange authorization code for tokens.
    """
    import httpx

    base_url = settings.KEYCLOAK_URL.rstrip("/")
    realm = settings.KEYCLOAK_REALM
    client_id = settings.KEYCLOAK_CLIENT_ID
    client_secret = getattr(settings, 'KEYCLOAK_CLIENT_SECRET', '')
    redirect_uri = f"{settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else 'http://localhost:3002'}/auth/callback"

    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        if response.status_code != 200:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Token exchange failed")

        tokens = response.json()

        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type"),
            "expires_in": tokens.get("expires_in"),
        }

