"""
Document Status Model
Tracks processing status for documents through the async ingestion pipeline.

Two-tier status:
- vector_status: Fast lane (seconds) - immediately queryable
- graph_status: Heavy lifting (minutes/hours) - eventual consistency
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class ProcessingStatus(str, Enum):
    """Status of document processing stages."""
    PENDING = "pending"           # Initial state, not yet started
    QUEUED = "queued"             # Waiting in rate-limited queue (graph indexing)
    PROCESSING = "processing"     # Currently being processed
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"             # Failed with error


class DocumentStatus(BaseModel):
    """
    Tracks document processing through the async ingestion pipeline.
    
    Supports "Eventual Consistency" architecture:
    - Tier 1 (Immediate): Vector embeddings - queryable in seconds
    - Tier 2 (Eventual): Knowledge graph - available in minutes/hours
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    workspace_id: str
    filename: Optional[str] = None
    
    # Two-tier status tracking
    vector_status: ProcessingStatus = ProcessingStatus.PENDING
    graph_status: ProcessingStatus = ProcessingStatus.PENDING
    
    # Progress tracking (0.0 - 1.0)
    vector_progress: float = 0.0
    graph_progress: float = 0.0
    
    # Task IDs for Celery job tracking
    vector_task_id: Optional[str] = None
    graph_task_id: Optional[str] = None
    
    # Error handling
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    vector_completed_at: Optional[datetime] = None
    graph_completed_at: Optional[datetime] = None
    
    # Metadata
    chunk_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    
    def is_vector_ready(self) -> bool:
        """Check if document is ready for vector search."""
        return self.vector_status == ProcessingStatus.COMPLETED
    
    def is_graph_ready(self) -> bool:
        """Check if document is ready for graph search."""
        return self.graph_status == ProcessingStatus.COMPLETED
    
    def is_fully_indexed(self) -> bool:
        """Check if both vector and graph indexing are complete."""
        return self.is_vector_ready() and self.is_graph_ready()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "filename": self.filename,
            "vector_status": self.vector_status.value,
            "graph_status": self.graph_status.value,
            "vector_progress": self.vector_progress,
            "graph_progress": self.graph_progress,
            "is_vector_ready": self.is_vector_ready(),
            "is_graph_ready": self.is_graph_ready(),
            "chunk_count": self.chunk_count,
            "entity_count": self.entity_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IngestJobResponse(BaseModel):
    """Response for async document ingestion."""
    status: str = "accepted"
    job_id: str
    document_id: str
    workspace_id: str
    message: str = "Document queued for processing. Vector search will be available shortly."


class DocumentStatusResponse(BaseModel):
    """Response for document status polling."""
    document_id: str
    workspace_id: str
    vector_status: ProcessingStatus
    graph_status: ProcessingStatus
    vector_progress: float
    graph_progress: float
    is_vector_ready: bool
    is_graph_ready: bool
    message: str
    chunk_count: int = 0
    entity_count: int = 0
