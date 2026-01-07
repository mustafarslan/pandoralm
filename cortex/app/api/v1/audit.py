
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.audit_service import AuditService
from app.models.audit import AuditLog

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[dict])
async def get_audit_logs(
    workspace_id: str = Query(..., description="Workspace ID"),
    user_id: Optional[str] = Query(None, description="Filter by User ID"),
    action: Optional[str] = Query(None, description="Filter by Action type"),
    resource_type: Optional[str] = Query(None, description="Filter by Resource Type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve audit logs for compliance and governance.
    """
    try:
        service = AuditService(db)
        logs = await service.get_logs(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            limit=limit,
            offset=offset
        )
        # Convert to list of dicts (Pydantic model would be better, but dict is explicit for now)
        return [log.to_dict() for log in logs]
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
