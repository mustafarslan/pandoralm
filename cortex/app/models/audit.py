
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class AuditLog(Base):
    """
    Audit Log Model.
    Tracks user actions for governance and compliance.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    user_id: Mapped[str] = mapped_column(String, index=True)
    workspace_id: Mapped[str] = mapped_column(String, index=True)
    layer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    action: Mapped[str] = mapped_column(String, index=True) # e.g. "query", "view", "ingest"
    
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String, nullable=True) # e.g. "document", "entity"
    
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "layer_id": self.layer_id,
            "action": self.action,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "details": self.details,
        }
