"""
Keycloak Security Module
JWT validation, OIDC integration, and RBAC
"""
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from functools import lru_cache
import time

from jose import jwt, JWTError, jwk
from jose.exceptions import JWKError
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings


@dataclass
class UserContext:
    """Authenticated user context from JWT."""
    sub: str  # Keycloak user ID
    email: str
    username: str
    name: str
    roles: List[str]
    groups: List[str]
    realm_access: Dict[str, Any]
    resource_access: Dict[str, Any]
    raw_token: str
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific realm role."""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(r in self.roles for r in roles)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(r in self.roles for r in roles)
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.has_role("admin")
    
    def is_vector_ops(self) -> bool:
        """Check if user has vector operations permission."""
        return self.has_role("vector-ops") or self.is_admin()


class KeycloakJWKS:
    """
    Fetches and caches JWKS (JSON Web Key Set) from Keycloak.
    
    JWKS contains the public keys used to verify JWT signatures.
    """
    
    def __init__(
        self,
        keycloak_url: str = None,
        realm: str = None,
        cache_ttl: int = 3600,
    ):
        self.keycloak_url = (keycloak_url or settings.KEYCLOAK_URL).rstrip("/")
        self.realm = realm or settings.KEYCLOAK_REALM
        self.cache_ttl = cache_ttl
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0
    
    @property
    def jwks_uri(self) -> str:
        """Get the JWKS endpoint URL."""
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
    
    @property
    def issuer(self) -> str:
        """Get the expected token issuer."""
        return f"{self.keycloak_url}/realms/{self.realm}"
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak with caching."""
        now = time.time()
        
        # Return cached if valid
        if self._jwks_cache and (now - self._cache_time) < self.cache_ttl:
            return self._jwks_cache
        
        # Fetch fresh JWKS
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._cache_time = now
                return self._jwks_cache
        except Exception as e:
            # Return stale cache if available
            if self._jwks_cache:
                return self._jwks_cache
            raise HTTPException(
                status_code=503,
                detail=f"Failed to fetch JWKS from Keycloak: {e}"
            )
    
    async def get_signing_key(self, kid: str) -> Optional[Dict[str, Any]]:
        """Get a specific signing key by key ID."""
        jwks = await self.get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        # Key not found, try refreshing cache
        self._jwks_cache = None
        jwks = await self.get_jwks()
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        
        return None


class JWTValidator:
    """
    Validates Keycloak JWT tokens.
    
    Verifies:
    - Token signature using JWKS
    - Token expiration
    - Token issuer
    - Token audience (optional)
    """
    
    def __init__(
        self,
        jwks: KeycloakJWKS = None,
        audience: str = None,
        verify_aud: bool = False,
    ):
        self.jwks = jwks or KeycloakJWKS()
        self.audience = audience or settings.KEYCLOAK_CLIENT_ID
        self.verify_aud = verify_aud
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token and return its claims.
        
        Raises HTTPException on validation failure.
        """
        try:
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise HTTPException(status_code=401, detail="Token missing key ID")
            
            # Get signing key
            signing_key = await self.jwks.get_signing_key(kid)
            
            if not signing_key:
                raise HTTPException(status_code=401, detail="Signing key not found")
            
            # Convert JWK to PEM for verification
            public_key = jwk.construct(signing_key)
            
            # Verify and decode token
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": self.verify_aud,
            }
            
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.audience if self.verify_aud else None,
                issuer=self.jwks.issuer,
                options=options,
            )
            
            return claims
            
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
        except JWKError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Key error: {str(e)}"
            )


# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Singleton instances
_jwks: Optional[KeycloakJWKS] = None
_validator: Optional[JWTValidator] = None


def get_jwks() -> KeycloakJWKS:
    global _jwks
    if _jwks is None:
        _jwks = KeycloakJWKS()
    return _jwks


def get_validator() -> JWTValidator:
    global _validator
    if _validator is None:
        _validator = JWTValidator()
    return _validator


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> Optional[UserContext]:
    """
    FastAPI dependency to get the current authenticated user.
    
    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    # DEV MODE: Skip all token validation for E2E testing
    import os
    if os.getenv("DEV_MODE_SKIP_AUTH", "").lower() == "true":
        return UserContext(
            sub="dev-user",
            email="dev@example.com",
            username="dev-admin",
            name="Dev Admin",
            roles=["admin", "vector-ops"],
            groups=["developers"],
            realm_access={"roles": ["admin", "vector-ops"]},
            resource_access={},
            raw_token="dev-token",
        )
    
    if not credentials:
        return None
    
    validator = get_validator()
    claims = await validator.validate_token(credentials.credentials)
    
    # Extract roles from realm_access
    realm_access = claims.get("realm_access", {})
    roles = realm_access.get("roles", [])
    
    # Extract groups
    groups = claims.get("groups", [])
    
    return UserContext(
        sub=claims.get("sub", ""),
        email=claims.get("email", ""),
        username=claims.get("preferred_username", ""),
        name=claims.get("name", ""),
        roles=roles,
        groups=groups,
        realm_access=realm_access,
        resource_access=claims.get("resource_access", {}),
        raw_token=credentials.credentials,
    )


async def require_auth(
    user: Optional[UserContext] = Depends(get_current_user),
) -> UserContext:
    """
    FastAPI dependency that requires authentication.
    
    Raises 401 if no valid token provided.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user


def require_roles(*required_roles: str):
    """
    Create a dependency that requires specific roles.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
    """
    async def check_roles(
        user: UserContext = Depends(require_auth),
    ) -> UserContext:
        if not user.has_any_role(list(required_roles)):
            raise HTTPException(
                status_code=403,
                detail=f"Required roles: {', '.join(required_roles)}"
            )
        return user
    
    return check_roles


def require_admin():
    """Dependency that requires admin role."""
    return require_roles("admin")


def require_vector_ops():
    """Dependency that requires vector-ops or admin role."""
    return require_roles("vector-ops", "admin")
