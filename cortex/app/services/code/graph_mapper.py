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
        from app.services.graphrag.neo4j_store import Entity, Relationship
        import uuid

        # 1. Create File Node (Idempotent)
        file_node_id = f"FILE::{workspace_id}::{chunk.file_path}"
        file_entity = Entity(
            id=file_node_id,
            name=chunk.file_path,
            type="File",
            description=f"Source file: {chunk.file_path}",
            source_documents=[chunk.document_id] if chunk.document_id else [],
            layer_id=chunk.layer_id,
            properties={"path": chunk.file_path}
        )
        self.store.upsert_entity(file_entity, workspace_id)
        
        # 2. Create Code Node (Class/Function)
        code_node_id = f"CODE::{workspace_id}::{chunk.id}"
        code_entity = Entity(
            id=code_node_id,
            name=chunk.metadata.get("raw_name", "anonymous"),
            type=chunk.node_type.capitalize(), # Class / Function
            description=f"{chunk.node_type} in {chunk.file_path}",
            source_documents=[chunk.document_id] if chunk.document_id else [],
            layer_id=chunk.layer_id,
            properties=chunk.metadata
        )
        self.store.upsert_entity(code_entity, workspace_id)
        
        # 3. Link File -> Code Node
        rel_contains = Relationship(
            id=f"REL::{uuid.uuid4()}",
            source_id=file_node_id,
            target_id=code_node_id,
            type="CONTAINS",
            description="File contains code chunk",
            layer_id=chunk.layer_id
        )
        self.store.upsert_relationship(rel_contains, workspace_id)
        
        # 4. Link Parent -> Child (if applicable)
        if chunk.parent_id:
            parent_node_id = f"CODE::{workspace_id}::{chunk.parent_id}"
            
            rel_parent = Relationship(
                id=f"REL::{uuid.uuid4()}",
                source_id=parent_node_id,
                target_id=code_node_id,
                type="HAS_METHOD" if chunk.node_type == "function" else "CONTAINS",
                description="Parent code structure contains child",
                layer_id=chunk.layer_id
            )
            self.store.upsert_relationship(rel_parent, workspace_id)

        # 5. Extract IMPORTS from file/context
        if chunk.metadata.get("imports"):
            for import_path in chunk.metadata["imports"]:
                import_node_id = f"MODULE::{workspace_id}::{import_path}"
                
                module_entity = Entity(
                    id=import_node_id,
                    name=import_path,
                    type="Module",
                    description=f"Imported module: {import_path}",
                    source_documents=[],
                    layer_id=chunk.layer_id,
                    properties={}
                )
                self.store.upsert_entity(module_entity, workspace_id)
                
                rel_imports = Relationship(
                    id=f"REL::{uuid.uuid4()}",
                    source_id=file_node_id,
                    target_id=import_node_id,
                    type="IMPORTS",
                    description="File imports module",
                    layer_id=chunk.layer_id
                )
                self.store.upsert_relationship(rel_imports, workspace_id)

        # 6. Extract INHERITS from class
        if chunk.node_type == "class" and chunk.metadata.get("bases"):
            for base_class in chunk.metadata["bases"]:
                base_node_id = f"CLASS_REF::{workspace_id}::{base_class}"
                
                base_entity = Entity(
                    id=base_node_id,
                    name=base_class,
                    type="Class",
                    description=f"Reference to class {base_class}",
                    source_documents=[],
                    layer_id=chunk.layer_id,
                    properties={"is_reference": True}
                )
                self.store.upsert_entity(base_entity, workspace_id)
                
                rel_inherits = Relationship(
                    id=f"REL::{uuid.uuid4()}",
                    source_id=code_node_id,
                    target_id=base_node_id,
                    type="INHERITS",
                    description="Class inherits from base",
                    layer_id=chunk.layer_id
                )
                self.store.upsert_relationship(rel_inherits, workspace_id)

        # 7. Extract CALLS from function body
        if chunk.metadata.get("calls"):
            for called_fn in chunk.metadata["calls"]:
                target_node_id = f"FUNCTION_REF::{workspace_id}::{called_fn}"
                
                func_ref_entity = Entity(
                    id=target_node_id,
                    name=called_fn,
                    type="Function",
                    description=f"Reference to function {called_fn}",
                    source_documents=[],
                    layer_id=chunk.layer_id,
                    properties={"is_reference": True}
                )
                self.store.upsert_entity(func_ref_entity, workspace_id)
                
                rel_calls = Relationship(
                    id=f"REL::{uuid.uuid4()}",
                    source_id=code_node_id,
                    target_id=target_node_id,
                    type="CALLS",
                    description="Function calls target",
                    layer_id=chunk.layer_id
                )
                self.store.upsert_relationship(rel_calls, workspace_id)

# Singleton
_graph_mapper = None

def get_code_graph_mapper() -> CodeGraphMapper:
    global _graph_mapper
    if _graph_mapper is None:
        _graph_mapper = CodeGraphMapper(get_neo4j_store())
    return _graph_mapper
