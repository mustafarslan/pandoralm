
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.audit import AuditLog

class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        user_id: str,
        workspace_id: str,
        action: str,
        layer_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a user action.
        """
        log_entry = AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            layer_id=layer_id,
            action=action,
            resource_id=resource_id,
            resource_type=resource_type,
            details=details,
            timestamp=datetime.utcnow()
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_logs(
        self,
        workspace_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Retrieve audit logs with filtering.
        """
        query = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            
        # Order by newest first
        query = query.order_by(desc(AuditLog.timestamp))
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_active_users(self, days: int = 30) -> List[str]:
        """
        Get list of users active in the last N days.
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = select(AuditLog.user_id).where(AuditLog.timestamp >= cutoff).distinct()
        
        result = await self.db.execute(query)
        return result.scalars().all()


async def audit_log_background(
    user_id: str,
    workspace_id: str,
    action: str,
    layer_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Background task wrapper for audit logging.
    Creates its own DB session scope.
    """
    from app.core.database import async_session_maker
    
    async with async_session_maker() as session:
        service = AuditService(session)
        await service.log_event(
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            layer_id=layer_id,
            resource_id=resource_id,
            resource_type=resource_type,
            details=details
        )
