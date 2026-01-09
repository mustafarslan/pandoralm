"""
Keycloak Identity Sync Service

Service to synchronize with Keycloak Admin API for role discovery.
Prevents "Ghost Permissions" by providing valid role options.
"""
import logging
from typing import List, Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class KeycloakSyncService:
    """
    Queries Keycloak Admin API for role discovery and synchronization.

    Used by Admin Console to:
    - Populate role dropdown in permission forms
    - Validate role patterns before saving
    - Audit role → layer mappings
    """

    def __init__(self):
        self.base_url = settings.KEYCLOAK_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self._admin_token: Optional[str] = None

    async def _get_admin_token(self) -> str:
        """
        Get admin access token using service account credentials.

        Uses client_credentials grant type with the admin-cli client
        or a custom service account client.
        """
        if self._admin_token:
            # In production, implement token refresh logic
            return self._admin_token

        token_url = f"{self.base_url}/realms/master/protocol/openid-connect/token"

        # Try with configured client first
        data = {
            "client_id": self.client_id or "admin-cli",
            "grant_type": "client_credentials",
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)

                if response.status_code == 200:
                    self._admin_token = response.json()["access_token"]
                    return self._admin_token
                else:
                    logger.error(f"Failed to get admin token: {response.text}")
                    raise Exception(f"Keycloak auth failed: {response.status_code}")

            except httpx.RequestError as e:
                logger.error(f"Keycloak connection error: {e}")
                raise Exception(f"Cannot connect to Keycloak: {e}")

    async def list_available_roles(self) -> List[str]:
        """
        Fetch all realm roles from Keycloak.

        Used to populate Admin Console dropdown, preventing typos
        in role_pattern fields.

        Returns:
            List of role names (e.g., ["admin", "user", "group:engineering"])
        """
        try:
            token = await self._get_admin_token()

            roles_url = f"{self.base_url}/admin/realms/{self.realm}/roles"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    roles_url,
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    roles = response.json()
                    return [r["name"] for r in roles]
                else:
                    logger.warning(f"Failed to fetch roles: {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error listing roles: {e}")
            return []

    async def list_available_groups(self) -> List[Dict[str, Any]]:
        """
        Fetch all groups from Keycloak.

        Groups can be used as role patterns with "group:" prefix.

        Returns:
            List of group objects with id, name, path
        """
        try:
            token = await self._get_admin_token()

            groups_url = f"{self.base_url}/admin/realms/{self.realm}/groups"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    groups_url,
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to fetch groups: {response.text}")
                    return []

        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            return []

    async def get_role_patterns(self) -> List[str]:
        """
        Get all valid role patterns for permission assignment.

        Combines:
        - Realm roles: "admin", "user", etc.
        - Group roles: "group:engineering", "group:hr", etc.
        - Wildcard patterns: "*", "group:*"

        Returns:
            List of valid role patterns
        """
        patterns = ["*"]  # Universal pattern

        # Add realm roles
        roles = await self.list_available_roles()
        patterns.extend(roles)

        # Add group-based patterns
        groups = await self.list_available_groups()
        for group in groups:
            # Convert group path to role pattern
            # e.g., "/Engineering" -> "group:engineering"
            group_name = group.get("name", "").lower().replace(" ", "-")
            patterns.append(f"group:{group_name}")
            patterns.append(f"group:{group_name}:*")  # Wildcard for subgroups

        return list(set(patterns))


# Singleton instance
keycloak_sync = KeycloakSyncService()


async def get_keycloak_sync() -> KeycloakSyncService:
    """FastAPI dependency for KeycloakSyncService."""
    return keycloak_sync
