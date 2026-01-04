"""
Code Graph Mapper Service.
Maps code structures (File -> Class -> Function) to Neo4j.
"""
import logging
from typing import List
from app.schemas.code import CodeChunk
from app.services.graphrag.neo4j_store import Neo4jGraphStore, get_neo4j_store

logger = logging.getLogger(__name__)

class CodeGraphMapper:
    """
    Handles mapping of CodeChunks to Neo4j graph nodes and relationships.
    """
    
    def __init__(self, neo4j_store: Neo4jGraphStore):
        self.store = neo4j_store

    def map_repo(self, chunks: List[CodeChunk], workspace_id: str):
        """
        Ingest a list of code chunks into the graph.
        """
        for chunk in chunks:
            try:
                self._process_chunk(chunk, workspace_id)
            except Exception as e:
                logger.error(f"Failed to map chunk {chunk.id}: {e}")

    def _process_chunk(self, chunk: CodeChunk, workspace_id: str):
        """
        Create logic specific to node type.
        """
        # 1. Create File Node (Idempotent)
        file_node_id = f"FILE::{workspace_id}::{chunk.file_path}"
        self.store.upsert_entity(
            id=file_node_id,
            name=chunk.file_path,
            type="File",
            description=f"Source file: {chunk.file_path}",
            workspace_id=workspace_id,
            layer_id=chunk.layer_id,
            source_id=chunk.document_id
        )
        
        # 2. Create Code Node (Class/Function)
        code_node_id = f"CODE::{workspace_id}::{chunk.id}"
        self.store.upsert_entity(
            id=code_node_id,
            name=chunk.metadata.get("raw_name", "anonymous"),
            type=chunk.node_type.capitalize(), # Class / Function
            description=f"{chunk.node_type} in {chunk.file_path}",
            workspace_id=workspace_id,
            layer_id=chunk.layer_id,
            source_id=chunk.document_id
        )
        
        # 3. Link File -> Code Node
        self.store.upsert_relationship(
            source_id=file_node_id,
            target_id=code_node_id,
            type="CONTAINS",
            workspace_id=workspace_id,
            layer_id=chunk.layer_id
        )
        
        # 4. Link Parent -> Child (if applicable)
        if chunk.parent_id:
            # We assume parent code chunk was processed or will be. 
            # We need a stable ID strategy for parents. 
            # Since CodeParser generates random UUIDs, valid linking relies on 
            # knowing the parent UUID. 
            # Implementation detail: CodeParser passes actual UUID of parent chunk.
            parent_node_id = f"CODE::{workspace_id}::{chunk.parent_id}"
            
            self.store.upsert_relationship(
                source_id=parent_node_id,
                target_id=code_node_id,
                type="HAS_METHOD" if chunk.node_type == "function" else "CONTAINS",
                workspace_id=workspace_id,
                layer_id=chunk.layer_id
            )

# Singleton
_graph_mapper = None

def get_code_graph_mapper() -> CodeGraphMapper:
    global _graph_mapper
    if _graph_mapper is None:
        _graph_mapper = CodeGraphMapper(get_neo4j_store())
    return _graph_mapper
