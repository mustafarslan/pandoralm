
import os
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
import logging

# Configuration (Env vars should be in config.py, but using os.getenv for now to be explicit)
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "pandora")
# Docker internal networking might require different URL for token validation depending on setup
# For validation, we typically need the public key which can be fetched from the issuer
ISSUER_URL = f"{KEYCLOAK_URL}/realms/{REALM}"

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)  # Don't auto-error, we handle it manually

class KeycloakVerifier:
    """Verifies Keycloak JWT tokens and enforcing RBAC."""
    
    def __init__(self):
        self._public_key = None
        
    async def get_public_key(self) -> str:
        """Fetch realm public key if not cached."""
        if self._public_key:
            return self._public_key
            
        try:
            # Fetch from standard OIDC endpoint
            # In a real app, use a robust OIDC library or cache this well
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{ISSUER_URL}")
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch Keycloak config: {resp.text}")
                    raise HTTPException(status_code=500, detail="Identity Provider Unavailable")
                
                data = resp.json()
                self._public_key = f"-----BEGIN PUBLIC KEY-----\n{data['public_key']}\n-----END PUBLIC KEY-----"
                return self._public_key
        except Exception as e:
            logger.error(f"Keycloak Connection Error: {e}")
            raise HTTPException(status_code=500, detail=f"Identity Provider Error: {str(e)}")

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Verify the Bearer token signature and expiration."""
        
        # In DEV/TEST mode, bypass auth entirely
        if os.getenv("AUTH_BYPASS", "false").lower() == "true" or os.getenv("DEV_MODE_SKIP_AUTH", "false").lower() == "true":
             return {
                 "sub": "test-user-id",
                 "realm_access": {"roles": ["vector_ops", "admin"]},
                 "email": "test@pandora.ai",
                 "groups": ["/Engineering", "/Legal"],
                 "attributes": {"workspace_id": ["eval-ws"]} # Simulating mapped attribute
             }
        
        # If not in dev mode and no credentials, reject
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = credentials.credentials

        public_key = await self.get_public_key()
        
        try:
            # Decode and verify
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="account", # Default client, or check if we need "pandora-cortex"
                options={"verify_aud": False} # Relax audience check for simplicity in this phase
            )
            return payload
        except JWTError as e:
            logger.warning(f"Invalid Token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def requires_role(self, role: str):
        """Dependency to check if user has a specific realm role."""
        async def role_checker(payload: Dict[str, Any] = Depends(self.verify_token)):
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            
            if role not in roles:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required role: {role}"
                )
            return payload
            
        return role_checker

# Singleton instance
verifier = KeycloakVerifier()
