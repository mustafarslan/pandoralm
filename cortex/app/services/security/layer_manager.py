"""
Layer Manager Service - Database-Driven ReBAC

Core engine for resolving user roles to Knowledge Layers.
Replaces static ROLE_LAYER_MAP with Postgres-backed dynamic resolution.
"""
from typing import List, Optional
from uuid import UUID
import fnmatch
import logging

from sqlalchemy import select, or_, text, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload

from app.models.layer import (
    Layer,
    LayerPermission,
    LayerType,
    AccessLevel,
    LayerCreate,
    PermissionCreate,
    QuotaTier,
    QuotaUpdate,
    BulkQuotaUpdate
)
from app.models.workspace_layer_mapping import WorkspaceLayerMapping

logger = logging.getLogger(__name__)


class LayerManager:
    """
    Database-driven ReBAC layer resolution.

    Resolves Keycloak roles to Knowledge Layers using:
    - Exact matches: role_pattern = "group:engineering"
    - Wildcard matches: role_pattern = "group:%" matches "group:engineering"
    - Glob patterns: `group:*` converted to SQL LIKE `group:%`
    """

    async def create_layer(
        self,
        data: LayerCreate,
        db: AsyncSession
    ) -> Layer:
        """
        Create a new Knowledge Layer.

        Args:
            data: Layer creation data (name, type, color)
            db: Database session

        Returns:
            Created Layer entity
        """
        layer = Layer(
            name=data.name,
            type=data.type,
            color=data.color
        )
        db.add(layer)
        await db.commit()
        await db.refresh(layer)

        logger.info(f"Created layer: {layer.name} ({layer.type.value})")
        return layer

    async def assign_permission(
        self,
        layer_id: UUID,
        role: str,
        level: AccessLevel,
        db: AsyncSession
    ) -> LayerPermission:
        """
        Grant a role access to a layer.

        Args:
            layer_id: Target layer UUID
            role: Role pattern (e.g., "group:engineering", "group:%")
            level: Access level (READ, WRITE, ADMIN)
            db: Database session

        Returns:
            Created LayerPermission entity
        """
        # Convert glob patterns to SQL LIKE patterns
        role_pattern = self._convert_glob_to_sql_like(role)

        perm = LayerPermission(
            layer_id=str(layer_id),
            role_pattern=role_pattern,
            access_level=level
        )
        db.add(perm)
        await db.commit()
        await db.refresh(perm)

        logger.info(f"Assigned permission: {role_pattern} -> {layer_id} ({level.value})")
        return perm

    async def revoke_permission(
        self,
        permission_id: UUID,
        db: AsyncSession
    ) -> bool:
        """
        Revoke a layer permission.

        Args:
            permission_id: Permission UUID to revoke
            db: Database session

        Returns:
            True if permission was revoked
        """
        result = await db.execute(
            delete(LayerPermission).where(LayerPermission.id == str(permission_id))
        )
        await db.commit()

        revoked = result.rowcount > 0
        if revoked:
            logger.info(f"Revoked permission: {permission_id}")
        return revoked

    async def resolve_layers_for_user(
        self,
        user_roles: List[str],
        db: AsyncSession,
        access_level: Optional[AccessLevel] = None,
        workspace_id: Optional[str] = None
    ) -> List[Layer]:
        """
        Core resolution engine with wildcard support and workspace context.

        Resolution algorithm:
        1. Find layers where user matches permissions (ReBAC)
        2. If workspace_id provided, filter to only layers mapped to workspace

        Args:
            user_roles: List of roles from Keycloak JWT
            db: Database session
            access_level: Optional filter for minimum access level
            workspace_id: Optional workspace context to filter layers

        Returns:
            List of Layer entities the user can access
        """
        if not user_roles and not workspace_id:
            # No roles & no context = only system public layers
            return await self._get_public_layers(db)

        # Build OR conditions for role matching
        conditions = []

        # If user has roles, check permissions
        if user_roles:
            for role in user_roles:
                # Exact match: role_pattern = 'group:engineering'
                conditions.append(LayerPermission.role_pattern == role)

                # Wildcard match: role LIKE role_pattern
                conditions.append(
                    text(f":role_{len(conditions)} LIKE REPLACE(role_pattern, '*', '%')")
                    .bindparams(**{f"role_{len(conditions)}": role})
                )

        # Base query joining Permissions
        query = (
            select(Layer)
            .join(LayerPermission)
            .where(Layer.is_soft_deleted == False)
            .distinct()
        )

        # Apply Role Conditions
        if conditions:
            query = query.where(or_(*conditions))

        # Apply Workspace Context Filter
        if workspace_id:
            query = query.join(WorkspaceLayerMapping).where(WorkspaceLayerMapping.workspace_id == workspace_id)

        # Optional access level filter
        if access_level:
            access_levels = self._get_access_level_hierarchy(access_level)
            query = query.where(LayerPermission.access_level.in_(access_levels))

        result = await db.execute(query)
        layers = list(result.scalars().all())

        # Always include public system layers
        public_layers = await self._get_public_layers(db)
        layer_ids = {l.id for l in layers}
        for public_layer in public_layers:
            if public_layer.id not in layer_ids:
                layers.append(public_layer)

        logger.debug(f"Resolved {len(layers)} layers for roles: {user_roles}")
        return layers

    async def get_layer(
        self,
        layer_id: UUID,
        db: AsyncSession
    ) -> Optional[Layer]:
        """Get a layer by ID."""
        result = await db.execute(
            select(Layer)
            .options(selectinload(Layer.permissions))
            .where(Layer.id == str(layer_id))
        )
        return result.scalar_one_or_none()

    async def list_layers(
        self,
        db: AsyncSession
    ) -> List[Layer]:
        """List all layers."""
        result = await db.execute(
            select(Layer).options(selectinload(Layer.permissions))
        )
        return list(result.scalars().all())

    async def _get_public_layers(self, db: AsyncSession) -> List[Layer]:
        """Get system public layers."""
        result = await db.execute(
            select(Layer)
            .join(LayerPermission)
            .where(LayerPermission.role_pattern == "*")
            .where(Layer.type == LayerType.SYSTEM)
            .where(Layer.is_soft_deleted == False)
        )
        return list(result.scalars().all())

    @staticmethod
    def _convert_glob_to_sql_like(pattern: str) -> str:
        """
        Convert glob pattern to SQL LIKE pattern.

        Examples:
            group:* -> group:%
            team:engineering:* -> team:engineering:%
        """
        return pattern.replace("*", "%")

    @staticmethod
    def _get_access_level_hierarchy(level: AccessLevel) -> List[AccessLevel]:
        """
        Get access levels that satisfy the minimum level.

        ADMIN > WRITE > READ
        If requiring READ, WRITE and ADMIN also satisfy.
        """
        hierarchy = {
            AccessLevel.READ: [AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN],
            AccessLevel.WRITE: [AccessLevel.WRITE, AccessLevel.ADMIN],
            AccessLevel.ADMIN: [AccessLevel.ADMIN],
        }
        return hierarchy.get(level, [level])

    async def create_private_layer_for_user(
        self,
        user_id: str,
        username: str,
        db: AsyncSession
    ) -> Layer:
        """Create a private USER layer for a new user."""
        existing = await self.get_user_private_layer(user_id, db)
        if existing:
            return existing

        layer = Layer(
            name=f"user-{username}",
            type=LayerType.USER,
            owner_user_id=user_id,
            quota_tier=QuotaTier.FREE,
            color="slate",
            storage_quota_bytes=104857600  # 100MB Default
        )
        db.add(layer)
        await db.commit()
        await db.refresh(layer)

        # Grant owner full ADMIN access
        # Uses explicit matching where user ID is expected in the claims/roles
        await self.assign_permission(
            layer.id,
            f"user:{user_id}",
            AccessLevel.ADMIN,
            db
        )
        return layer

    async def get_user_private_layer(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Optional[Layer]:
        """Get a user's private layer."""
        result = await db.execute(
            select(Layer)
            .where(Layer.owner_user_id == user_id)
            .where(Layer.type == LayerType.USER)
            .where(Layer.is_soft_deleted == False)
        )
        return result.scalar_one_or_none()

    async def check_quota_exceeded(
        self,
        layer_id: UUID,
        db: AsyncSession
    ) -> bool:
        """Check if layer has exceeded its storage quota."""
        layer = await self.get_layer(layer_id, db)
        if not layer:
            return False

        if layer.storage_used_bytes >= layer.storage_quota_bytes:
            return True

        return False

    async def update_storage_used(
        self,
        layer_id: UUID,
        delta_bytes: int,
        db: AsyncSession
    ) -> int:
        """Update storage usage for a layer."""
        layer = await self.get_layer(layer_id, db)
        if layer:
            layer.storage_used_bytes += delta_bytes
            if layer.storage_used_bytes < 0:
                layer.storage_used_bytes = 0
            await db.commit()
            return layer.storage_used_bytes
        return 0

    async def update_layer_quota(
        self,
        layer_id: UUID,
        data: QuotaUpdate,
        db: AsyncSession
    ) -> Optional[Layer]:
        """Update a layer's quota settings."""
        layer = await self.get_layer(layer_id, db)
        if not layer:
            return None

        if data.quota_tier:
            layer.quota_tier = data.quota_tier

        if data.storage_quota_bytes is not None:
            layer.storage_quota_bytes = data.storage_quota_bytes

        await db.commit()
        await db.refresh(layer)
        return layer

    async def bulk_update_quotas(
        self,
        data: BulkQuotaUpdate,
        db: AsyncSession
    ) -> int:
        """
        Bulk update quotas for all layers of a specific type.
        Returns number of updated layers.
        """
        # Build update values
        values = {}
        if data.quota_tier:
            values["quota_tier"] = data.quota_tier
        values["storage_quota_bytes"] = data.storage_quota_bytes

        # Execute bulk update
        stmt = (
            update(Layer)
            .where(Layer.type == data.type)
            .values(**values)
        )

        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def cleanup_soft_deleted_layers(
        self,
        db: AsyncSession,
        retention_days: int = 30
    ) -> int:
        """
        Hard delete layers that have been soft-deleted for longer than retention period.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        stmt = (
            delete(Layer)
            .where(Layer.is_soft_deleted == True)
            .where(Layer.deleted_at <= cutoff_date)
        )

        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount > 0:
            logger.info(f"Reaper: Cleaned up {result.rowcount} expired layers (older than {retention_days} days)")

        return result.rowcount





# Singleton instance for dependency injection
layer_manager = LayerManager()


async def get_layer_manager() -> LayerManager:
    """FastAPI dependency for LayerManager."""
    return layer_manager
