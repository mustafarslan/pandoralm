"""
Document Status Service
Redis-based status tracking for async document ingestion pipeline.
"""
import json
import logging
from datetime import datetime
from typing import Optional, List

import redis

from app.core.config import settings
from app.models.document_status import DocumentStatus, ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentStatusService:
    """
    Redis-based service for tracking document processing status.
    
    Uses Redis for fast, in-memory status storage that's already
    available for Celery. Status keys expire after 7 days.
    """
    
    KEY_PREFIX = "docstatus:"
    WORKSPACE_INDEX_PREFIX = "docstatus:ws:"
    DEFAULT_TTL = 60 * 60 * 24 * 7  # 7 days
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Lazy Redis client initialization."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client
    
    def _key(self, document_id: str) -> str:
        """Generate Redis key for document status."""
        return f"{self.KEY_PREFIX}{document_id}"
    
    def _workspace_key(self, workspace_id: str) -> str:
        """Generate Redis key for workspace document index."""
        return f"{self.WORKSPACE_INDEX_PREFIX}{workspace_id}"
    
    def create(self, document_id: str, workspace_id: str, filename: str = None) -> DocumentStatus:
        """Create a new document status record."""
        status = DocumentStatus(
            document_id=document_id,
            workspace_id=workspace_id,
            filename=filename,
            created_at=datetime.utcnow(),
        )
        
        # Store in Redis
        self.client.setex(
            self._key(document_id),
            self.DEFAULT_TTL,
            status.model_dump_json(),
        )
        
        # Add to workspace index
        self.client.sadd(self._workspace_key(workspace_id), document_id)
        
        logger.info(f"Created document status: {document_id} for workspace {workspace_id}")
        return status
    
    def get(self, document_id: str) -> Optional[DocumentStatus]:
        """Get document status by ID."""
        data = self.client.get(self._key(document_id))
        if not data:
            return None
        return DocumentStatus.model_validate_json(data)
    
    def update(self, document_id: str, **updates) -> Optional[DocumentStatus]:
        """Update document status fields."""
        status = self.get(document_id)
        if not status:
            logger.warning(f"Document status not found: {document_id}")
            return None
        
        # Apply updates
        updates["updated_at"] = datetime.utcnow()
        
        for key, value in updates.items():
            if hasattr(status, key):
                setattr(status, key, value)
        
        # Store updated status
        self.client.setex(
            self._key(document_id),
            self.DEFAULT_TTL,
            status.model_dump_json(),
        )
        
        logger.debug(f"Updated document status: {document_id}")
        return status
    
    def update_vector_status(
        self,
        document_id: str,
        status: ProcessingStatus,
        progress: float = None,
        chunk_count: int = None,
        task_id: str = None,
        error_message: str = None,
    ) -> Optional[DocumentStatus]:
        """Update vector processing status."""
        updates = {"vector_status": status}
        
        if progress is not None:
            updates["vector_progress"] = progress
        if chunk_count is not None:
            updates["chunk_count"] = chunk_count
        if task_id is not None:
            updates["vector_task_id"] = task_id
        if error_message is not None:
            updates["error_message"] = error_message
        if status == ProcessingStatus.COMPLETED:
            updates["vector_completed_at"] = datetime.utcnow()
            updates["vector_progress"] = 1.0
        
        return self.update(document_id, **updates)
    
    def update_graph_status(
        self,
        document_id: str,
        status: ProcessingStatus,
        progress: float = None,
        entity_count: int = None,
        relationship_count: int = None,
        task_id: str = None,
        error_message: str = None,
    ) -> Optional[DocumentStatus]:
        """Update graph processing status."""
        updates = {"graph_status": status}
        
        if progress is not None:
            updates["graph_progress"] = progress
        if entity_count is not None:
            updates["entity_count"] = entity_count
        if relationship_count is not None:
            updates["relationship_count"] = relationship_count
        if task_id is not None:
            updates["graph_task_id"] = task_id
        if error_message is not None:
            updates["error_message"] = error_message
        if status == ProcessingStatus.COMPLETED:
            updates["graph_completed_at"] = datetime.utcnow()
            updates["graph_progress"] = 1.0
        
        return self.update(document_id, **updates)
    
    def get_by_workspace(self, workspace_id: str) -> List[DocumentStatus]:
        """Get all document statuses for a workspace."""
        doc_ids = self.client.smembers(self._workspace_key(workspace_id))
        results = []
        
        for doc_id in doc_ids:
            status = self.get(doc_id)
            if status:
                results.append(status)
        
        return results
    
    def delete(self, document_id: str) -> bool:
        """Delete document status."""
        status = self.get(document_id)
        if not status:
            return False
        
        # Remove from workspace index
        self.client.srem(self._workspace_key(status.workspace_id), document_id)
        
        # Delete status
        self.client.delete(self._key(document_id))
        
        logger.info(f"Deleted document status: {document_id}")
        return True


# Singleton instance
_service: Optional[DocumentStatusService] = None


def get_document_status_service() -> DocumentStatusService:
    """Get or create the document status service singleton."""
    global _service
    if _service is None:
        _service = DocumentStatusService()
    return _service
