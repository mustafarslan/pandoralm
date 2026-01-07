"""
Schemas for Code Intelligence Chunks and Entities.
Inherits from SecureVectorChunk to ensure layer_id security.
"""
from typing import Optional, List
from pydantic import Field
from dataclasses import dataclass
from app.services.vector_store import VectorChunk

@dataclass
class CodeChunk(VectorChunk):
    """
    Represents a chunk of code (Class, Function, or Block).
    Inherits secure fields (layer_id, access_roles) from VectorChunk.
    """
    node_type: str = "block"
    language: str = "text"
    start_line: int = 0
    end_line: int = 0
    file_path: str = ""
    parent_id: Optional[str] = None
    signature: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for LanceDB."""
        base = super().to_dict()
        base.update({
            "node_type": self.node_type,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "file_path": self.file_path,
            "parent_id": self.parent_id or "",
            "signature": self.signature or "",
        })
        return base

class CodeEntity:
    """
    Represents a code entity for the Knowledge Graph (Neo4j).
    """
    def __init__(
        self,
        id: str,
        name: str,
        type: str,
        file_path: str,
        layer_id: str,
        signature: Optional[str] = None,
        workspace_id: str = "default"
    ):
        self.id = id
        self.name = name
        self.type = type
        self.file_path = file_path
        self.layer_id = layer_id
        self.signature = signature
        self.workspace_id = workspace_id
