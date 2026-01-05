"""
Workspace Layer Service
Manages the relationship between workspaces and knowledge layers.
Phase 5-3: Federated Knowledge Architecture
"""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.layer import Layer, LayerType, AccessLevel
from app.models.workspace_layer_mapping import WorkspaceLayerMapping
from app.services.security.layer_manager import layer_manager

logger = logging.getLogger(__name__)


class WorkspaceLayerService:
    """
    Manages the relationship between workspaces and knowledge layers.
    
    This service implements the "Federated Knowledge" logic where workspaces
    subscribe to global layers and own private layers.
    """
    
    async def get_workspace_layers(
        self, 
        workspace_id: str, 
        db: AsyncSession
    ) -> List[Layer]:
        """
        Get all layers accessible by a workspace.
        Returns the actual Layer objects.
        """
        stmt = (
            select(Layer)
            .join(WorkspaceLayerMapping)
            .where(WorkspaceLayerMapping.workspace_id == workspace_id)
            .where(Layer.is_soft_deleted == False)
        )
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def add_layer_to_workspace(
        self,
        workspace_id: str,
        layer_id: UUID,
        access_mode: str,
        db: AsyncSession
    ) -> WorkspaceLayerMapping:
        """
        Add a layer to a workspace's accessible layers.
        Idempotent: if mapping exists, updates access_mode.
        """
        # Check if mapping exists
        stmt = (
            select(WorkspaceLayerMapping)
            .where(WorkspaceLayerMapping.workspace_id == workspace_id)
            .where(WorkspaceLayerMapping.layer_id == str(layer_id))
        )
        result = await db.execute(stmt)
        mapping = result.scalar_one_or_none()
        
        if mapping:
            map_obj = mapping
            map_obj.access_mode = access_mode
            logger.info(f"Updated mapping: Workspace {workspace_id} -> Layer {layer_id} ({access_mode})")
        else:
            map_obj = WorkspaceLayerMapping(
                workspace_id=workspace_id,
                layer_id=str(layer_id),
                access_mode=access_mode
            )
            db.add(map_obj)
            logger.info(f"Created mapping: Workspace {workspace_id} -> Layer {layer_id} ({access_mode})")
            
        await db.commit()
        await db.refresh(map_obj)
        return map_obj

    async def remove_layer_from_workspace(
        self,
        workspace_id: str,
        layer_id: UUID,
        db: AsyncSession
    ) -> bool:
        """
        Remove layer from workspace.
        """
        stmt = (
            delete(WorkspaceLayerMapping)
            .where(WorkspaceLayerMapping.workspace_id == workspace_id)
            .where(WorkspaceLayerMapping.layer_id == str(layer_id))
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Removed mapping: Workspace {workspace_id} -> Layer {layer_id}")
            
        return deleted

    async def initialize_workspace_layers(
        self,
        workspace_id: str,
        user_id: str,
        username: str,
        db: AsyncSession
    ) -> List[WorkspaceLayerMapping]:
        """
        Initialize layers for a new workspace.
        
        Standard Federated Setup:
        1. Map to SYSTEM layer (Read-Only)
        2. Map to ORGANIZATION layer (Read-Only)
        3. Create/Map to USER Private Layer (Write/Admin)
        """
        mappings = []
        
        # 1. Get Global Layers (SYSTEM + ORGANIZATION)
        stmt = (
            select(Layer)
            .where(Layer.is_global == True)
            .where(Layer.is_soft_deleted == False)
        )
        result = await db.execute(stmt)
        global_layers = result.scalars().all()
        
        for layer in global_layers:
            # All global layers are read-only by default for workspaces
            # (unless specific overrides exist, which is handled by RBAC, not mapping)
            m = await self.add_layer_to_workspace(workspace_id, layer.id, "read", db)
            mappings.append(m)
            
        # 2. Get/Create User Private Layer
        user_layer = await layer_manager.create_private_layer_for_user(user_id, username, db)
        
        # 3. Map User Layer (Write Access)
        m_user = await self.add_layer_to_workspace(workspace_id, user_layer.id, "write", db)
        mappings.append(m_user)
        
        logger.info(f"Initialized {len(mappings)} layers for workspace {workspace_id}")
        return mappings

    async def initialize_defaults(self, slug: str) -> bool:
        """
        Auto-initialize layers for a workspace by slug.
        Creates its own DB session to ensure isolation.
        """
        from app.core.database import async_session_maker
        # We use the slug as the workspace_id for mappings to maintain compatibility
        # with the frontend which uses slugs for routing.
        
        try:
            async with async_session_maker() as db:
                # Use 'system' user for default initialization
                # In real flow, this should come from context, but for auto-init
                # we ensure the workspace works out of the box.
                await self.initialize_workspace_layers(slug, "system", "system", db)
                return True
        except Exception as e:
            logger.error(f"Failed to auto-initialize layers for {slug}: {e}")
            return False

# Singleton
workspace_layer_service = WorkspaceLayerService()

async def get_workspace_layer_service() -> WorkspaceLayerService:
    return workspace_layer_service
