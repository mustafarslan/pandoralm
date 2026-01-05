"""
Workspace Layer Mapping Model
Maps workspaces to accessible knowledge layers (Federated Knowledge Architecture).
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class WorkspaceLayerMapping(Base):
    """
    Maps workspaces to accessible knowledge layers.
    
    This is the core of the Federated Knowledge architecture:
    - Workspaces don't "own" data anymore
    - They reference shared global layers or private user layers
    - Each mapping can specify read/write access
    """
    __tablename__ = "workspace_layer_mappings"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    workspace_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    layer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("layers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    access_mode: Mapped[str] = mapped_column(String(20), default="read")  # "read" | "write"
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    
    # Relationships
    layer: Mapped["Layer"] = relationship("Layer", back_populates="workspace_mappings")

    # Index for fast lookups of layers for a workspace
    __table_args__ = (
        Index("ix_workspace_layer_mappings_workspace_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceLayerMapping {self.workspace_id} -> {self.layer_id} ({self.access_mode})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "layer_id": self.layer_id,
            "access_mode": self.access_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
