"""
Authentication Middleware
Injects user context into requests
"""
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.security import get_validator, UserContext


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts and validates JWT tokens.

    Attaches user context to request.state.user for all routes.
    Does not block requests - authentication is optional at middleware level.
    Use dependencies for required auth.
    """

    # Paths that skip auth processing entirely
    SKIP_PATHS = [
        "/health",
        "/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for certain paths
        if any(request.url.path.startswith(p) for p in self.SKIP_PATHS):
            request.state.user = None
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

            try:
                # Validate token
                if settings.DEV_MODE_SKIP_AUTH:
                    # Mock User for E2E Testing
                    request.state.user = UserContext(
                        sub="test-user-id",
                        email="test@pandora.local",
                        username="testuser",
                        name="Test User",
                        roles=["admin", "group:engineering"], # Give admin access for tests
                        groups=["group:engineering"],
                        realm_access={"roles": ["admin", "group:engineering"]},
                        resource_access={},
                        raw_token=token,
                    )
                else:
                    validator = get_validator()
                    claims = await validator.validate_token(token)

                    # Build user context
                    realm_access = claims.get("realm_access", {})

                    request.state.user = UserContext(
                        sub=claims.get("sub", ""),
                        email=claims.get("email", ""),
                        username=claims.get("preferred_username", ""),
                        name=claims.get("name", ""),
                        roles=realm_access.get("roles", []),
                        groups=claims.get("groups", []),
                        realm_access=realm_access,
                        resource_access=claims.get("resource_access", {}),
                        raw_token=token,
                    )
            except Exception:
                # Invalid token - set user to None
                # Endpoint dependencies will handle auth requirements
                request.state.user = None
        else:
            request.state.user = None

        return await call_next(request)


def get_user_from_request(request: Request) -> Optional[UserContext]:
    """Helper to get user from request state."""
    return getattr(request.state, "user", None)
