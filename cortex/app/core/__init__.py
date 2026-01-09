"""
Core Package
Configuration, security, and middleware
"""
from app.core.config import settings
from app.core.security import (
    UserContext,
    JWTValidator,
    KeycloakJWKS,
    get_current_user,
    require_auth,
    require_roles,
    require_admin,
    require_vector_ops,
)
from app.core.rbac import Permission, check_permission
from app.core.middleware import AuthMiddleware, get_user_from_request

__all__ = [
    # Config
    "settings",

    # Security
    "UserContext",
    "JWTValidator",
    "KeycloakJWKS",
    "get_current_user",
    "require_auth",
    "require_roles",
    "require_admin",
    "require_vector_ops",

    # RBAC
    "Permission",
    "check_permission",

    # Middleware
    "AuthMiddleware",
    "get_user_from_request",
]
