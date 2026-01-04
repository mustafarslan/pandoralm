"""
Vector Schema Definitions (V2)
Phase 5-3: Enterprise Security & Governance

LanceDB schema with layer_id for multi-tenant vector partitioning.
"""
from typing import List, Optional
from datetime import datetime

from lancedb.pydantic import LanceModel, Vector


class VectorSchemaV2(LanceModel):
    """
    Secure vector schema with Knowledge Layer partitioning.
    
    Key fields for ReBAC:
    - layer_id: Partition key for layer-based filtering
    - access_permissions: Fine-grained ACL (optional, for future use)
    
    All queries MUST use prefilter=True on layer_id for security.
    """
    # Primary fields
    id: str
    content: str
    embedding: Vector(1536)  # OpenAI text-embedding-3-small dimension
    
    # Document context
    document_id: str
    workspace_id: str  # Legacy field for backwards compatibility
    
    # Security fields (Phase 5-3)
    layer_id: str = "default"  # Partition key for ReBAC
    access_permissions: List[str] = []  # Fine-grained ACL (future)
    visibility: str = "private"  # "public" or "private"
    
    # Metadata
    metadata: str = "{}"  # JSON-serialized metadata
    created_at: str = ""  # ISO timestamp
    
    @classmethod
    def from_chunk(
        cls,
        id: str,
        content: str,
        embedding: List[float],
        document_id: str,
        workspace_id: str,
        layer_id: str = "default",
        access_permissions: Optional[List[str]] = None,
        visibility: str = "private",
        metadata: str = "{}",
    ) -> "VectorSchemaV2":
        """Factory method to create a schema instance from chunk data."""
        return cls(
            id=id,
            content=content,
            embedding=embedding,
            document_id=document_id,
            workspace_id=workspace_id,
            layer_id=layer_id,
            access_permissions=access_permissions or [],
            visibility=visibility,
            metadata=metadata,
            created_at=datetime.utcnow().isoformat(),
        )


# Legacy schema for V1 compatibility
class VectorSchemaV1(LanceModel):
    """Legacy vector schema without layer support."""
    id: str
    content: str
    embedding: Vector(1536)
    document_id: str
    workspace_id: str
    metadata: str = "{}"
    created_at: str = ""
