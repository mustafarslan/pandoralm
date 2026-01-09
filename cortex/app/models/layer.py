from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import uuid4
import enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    event,
    BigInteger,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models.workspace_layer_mapping import WorkspaceLayerMapping


class LayerType(str, enum.Enum):
    """Types of Knowledge Layers for organizational hierarchy."""
    SYSTEM = "SYSTEM"           # Global system layers (e.g., public docs)
    ORGANIZATION = "ORGANIZATION"  # Org-wide layers (e.g., company policies)
    TEAM = "TEAM"               # Team-specific layers (e.g., engineering)
    USER = "USER"               # User-private layers (personal workspace)


class AccessLevel(str, enum.Enum):
    """Permission levels for layer access."""
    READ = "READ"       # Can query vectors in this layer
    WRITE = "WRITE"     # Can add/update vectors in this layer
    ADMIN = "ADMIN"     # Can manage permissions for this layer


class QuotaTier(str, enum.Enum):
    """Storage quota tiers."""
    FREE = "FREE"           # 100 MB (User Default)
    PRO = "PRO"             # 10 GB
    ENTERPRISE = "ENTERPRISE" # 1 TB


class Layer(Base):
    """
    Knowledge Layer for vector partitioning.

    Each layer represents a logical partition of the vector store,
    enabling multi-tenant data isolation and ReBAC enforcement.
    """
    __tablename__ = "layers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[LayerType] = mapped_column(
        Enum(LayerType),
        nullable=False,
        default=LayerType.TEAM
    )
    color: Mapped[str] = mapped_column(String(50), default="slate")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # New fields (Phase 5-3 ReBAC & Governance)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    quota_tier: Mapped[QuotaTier] = mapped_column(
        Enum(QuotaTier),
        default=QuotaTier.FREE
    )
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, default=104857600)  # 100MB
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    # Federated Knowledge (Phase 6)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    """
    Global layers are shared across all workspaces.
    Only SYSTEM/ORGANIZATION/ENGINEERING types should be global.
    USER layers are always private.
    """

    is_soft_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    permissions: Mapped[List["LayerPermission"]] = relationship(
        "LayerPermission",
        back_populates="layer",
        cascade="all, delete-orphan"
    )

    workspace_mappings: Mapped[List["WorkspaceLayerMapping"]] = relationship(
        "WorkspaceLayerMapping",
        back_populates="layer",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Layer {self.name} ({self.type.value})>"

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "owner_user_id": self.owner_user_id,
            "quota_tier": self.quota_tier.value,
            "storage_quota_bytes": self.storage_quota_bytes,
            "storage_used_bytes": self.storage_used_bytes,
            "is_global": self.is_global,
            "is_soft_deleted": self.is_soft_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class LayerPermission(Base):
    """
    Permission mapping from Keycloak roles to Layer access.

    Supports:
    - Exact matches: role_pattern = "group:engineering"
    - Wildcard matches: role_pattern = "group:%" matches "group:*"

    The role_pattern column has a B-Tree index for fast lookup.
    """
    __tablename__ = "layer_permissions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    layer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("layers.id", ondelete="CASCADE"),
        nullable=False
    )
    role_pattern: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True  # B-Tree index for fast role matching
    )
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel),
        nullable=False,
        default=AccessLevel.READ
    )

    # Relationships
    layer: Mapped["Layer"] = relationship("Layer", back_populates="permissions")

    # Explicit B-Tree index on role_pattern for query optimization
    __table_args__ = (
        Index("ix_layer_permissions_role_pattern_btree", "role_pattern"),
    )

    def __repr__(self) -> str:
        return f"<LayerPermission {self.role_pattern} -> {self.layer_id} ({self.access_level.value})>"

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "id": self.id,
            "layer_id": self.layer_id,
            "role_pattern": self.role_pattern,
            "access_level": self.access_level.value,
        }


# Pydantic schemas for API requests/responses
from pydantic import BaseModel, Field
from typing import Optional


class LayerCreate(BaseModel):
    """Request schema for creating a layer."""
    name: str = Field(..., min_length=1, max_length=255)
    type: LayerType = LayerType.TEAM
    color: str = "slate"


class LayerResponse(BaseModel):
    """Response schema for layer data."""
    id: str
    name: str
    type: LayerType
    color: str
    created_at: Optional[datetime] = None

    # Phase 5-3 Fields
    owner_user_id: Optional[str] = None
    quota_tier: QuotaTier = QuotaTier.FREE
    storage_quota_bytes: int
    storage_used_bytes: int
    is_soft_deleted: bool
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    """Request schema for adding a permission."""
    role_pattern: str = Field(..., min_length=1, max_length=255)
    access_level: AccessLevel = AccessLevel.READ


class PermissionResponse(BaseModel):
    """Response schema for permission data."""
    id: str
    layer_id: str
    role_pattern: str
    access_level: AccessLevel

    class Config:
        from_attributes = True


class QuotaUpdate(BaseModel):
    """Request schema for updating layer quota."""
    quota_tier: Optional[QuotaTier] = None
    storage_quota_bytes: Optional[int] = Field(None, ge=1048576) # Min 1MB


class BulkQuotaUpdate(BaseModel):
    """Request schema for bulk updating quotas by type."""
    type: LayerType
    quota_tier: Optional[QuotaTier] = None
    storage_quota_bytes: int = Field(..., ge=1048576)

