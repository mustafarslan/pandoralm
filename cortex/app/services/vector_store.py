"""
LanceDB Vector Store Service
Embedded vector database for semantic search
"""
import os
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import lancedb
from lancedb.table import Table
import pyarrow as pa

from app.core.config import settings
from app.core.telemetry import trace_span

# Export for schemas
__all__ = ["LanceDBStore", "VectorChunk", "SearchResult", "get_vector_store"]


@dataclass
class VectorChunk:
    """A document chunk with its embedding."""
    id: str
    content: str
    embedding: List[float]
    document_id: str
    workspace_id: str
    layer_id: str = "default"  # Knowledge Layer
    access_roles: List[str] = field(default_factory=list) # RBAC 
    visibility: str = "private" # public/private/restricted
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "document_id": self.document_id,
            "workspace_id": self.workspace_id,
            "layer_id": self.layer_id,
            "access_roles": self.access_roles,
            "visibility": self.visibility,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass  
class SearchResult:
    """Result from similarity search."""
    chunk: VectorChunk
    score: float
    distance: float


class LanceDBStore:
    """
    LanceDB-backed vector store for PandoraLM.
    
    Provides embedded vector storage with:
    - Zero-copy reads via Arrow format
    - Persistent storage on disk
    - Efficient similarity search
    """
    
    # Arrow schema for vector table
    SCHEMA = pa.schema([
        pa.field("id", pa.string()),
        pa.field("content", pa.string()),
        pa.field("embedding", pa.list_(pa.float32(), 384)),
        pa.field("document_id", pa.string()),
        pa.field("workspace_id", pa.string()),
        pa.field("layer_id", pa.string()),
        pa.field("access_roles", pa.list_(pa.string())),
        pa.field("visibility", pa.string()),
        pa.field("metadata", pa.string()),  # JSON string
        pa.field("created_at", pa.string()),
    ])
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.LANCEDB_PATH
        self._db: Optional[lancedb.DBConnection] = None
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        os.makedirs(self.db_path, exist_ok=True)
    
    @property
    def db(self) -> lancedb.DBConnection:
        """Lazy initialization of LanceDB connection."""
        if self._db is None:
            if settings.LANCEDB_URI and settings.LANCEDB_URI.startswith("s3://"):
                # Connect to S3/MinIO
                storage_options = {
                    "aws_endpoint": settings.AWS_ENDPOINT_URL,
                    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                    "aws_region": settings.AWS_REGION,
                    "allow_http": "true" if "http://" in settings.AWS_ENDPOINT_URL else "false",
                }
                # Filter out empty keys
                storage_options = {k: v for k, v in storage_options.items() if v}
                
                self._db = lancedb.connect(settings.LANCEDB_URI, storage_options=storage_options)
            else:
                # Local filesystem
                self._db = lancedb.connect(self.db_path)
        return self._db
    
    def _get_table_name(self, workspace_id: str) -> str:
        """Get table name for a workspace."""
        # Sanitize workspace_id for table name
        safe_id = workspace_id.replace("-", "_").replace(" ", "_")
        # Use configured table prefix (e.g. vectors vs vectors_v2)
        prefix = settings.LANCEDB_TABLE
        return f"{prefix}_{safe_id}"
    
    def _ensure_table(self, workspace_id: str) -> Table:
        """Ensure table exists for workspace, create if not."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            # Create empty table with schema
            import logging
            logger = logging.getLogger("uvicorn.error")
            logger.info(f"DEBUG: Creating table {table_name} with schema: {self.SCHEMA}")
            return self.db.create_table(table_name, schema=self.SCHEMA)
        
        tbl = self.db.open_table(table_name)
        # Verify schema
        import logging
        logger = logging.getLogger("uvicorn.error") 
        logger.info(f"DEBUG: Opened table {table_name} with schema: {tbl.schema}")
        return tbl
    
    # ========================================
    # Collection Management
    # ========================================
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all vector collections (tables)."""
        collections = []
        prefix = settings.LANCEDB_TABLE
        
        for table_name in self.db.table_names():
            if table_name.startswith(f"{prefix}_"):
                table = self.db.open_table(table_name)
                # Recover workspace_id
                workspace_id = table_name.replace(f"{prefix}_", "").replace("_", "-")
                
                # Get stats
                try:
                    count = table.count_rows()
                except Exception:
                    count = 0
                
                collections.append({
                    "name": table_name,
                    "workspace_id": workspace_id,
                    "total_chunks": count,
                    "dimensions": 1536,  # Default OpenAI dimensions
                    "storage_bytes": self._get_table_size(workspace_id),
                })
        
        return collections

    def _get_table_size(self, workspace_id: str) -> int:
        """Calculate storage size for a workspace table."""
        table_name = self._get_table_name(workspace_id)
        storage_path = os.path.join(self.db_path, f"{table_name}.lance")
        
        storage_bytes = 0
        if os.path.exists(storage_path):
            try:
                for root, dirs, files in os.walk(storage_path):
                    for f in files:
                        storage_bytes += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
        
        return storage_bytes
    
    def get_collection_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Get detailed stats for a collection."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return {
                "name": table_name,
                "workspace_id": workspace_id,
                "total_chunks": 0,
                "dimensions": 0,
                "storage_bytes": 0,
                "exists": False,
            }
        
        table = self.db.open_table(table_name)
        count = table.count_rows()
        
        # Estimate storage size
        storage_path = os.path.join(self.db_path, f"{table_name}.lance")
        storage_bytes = 0
        if os.path.exists(storage_path):
            for root, dirs, files in os.walk(storage_path):
                for f in files:
                    storage_bytes += os.path.getsize(os.path.join(root, f))
        
        return {
            "name": table_name,
            "workspace_id": workspace_id,
            "total_chunks": count,
            "dimensions": 1536,
            "storage_bytes": storage_bytes,
            "exists": True,
        }
    
    def delete_collection(self, workspace_id: str) -> bool:
        """Delete a collection."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name in self.db.table_names():
            self.db.drop_table(table_name)
            return True
        return False
    
    # ========================================
    # Chunk Operations
    # ========================================
    
    async def add_chunks_batch(self, chunks_data: List[dict], workspace_id: str) -> int:
        """Add a batch of chunks from dictionaries (Async wrapper)."""
        if not chunks_data:
            return 0
            
        # Infer workspace_id from first chunk (all must belong to same workspace)
        # workspace_id = chunks_data[0].get("workspace_id", "default")
        
        vector_chunks = []
        for c in chunks_data:
            vector_chunks.append(VectorChunk(
                id=c["id"],
                content=c["content"],
                embedding=c["embedding"],
                document_id=c["document_id"],
                workspace_id=c["workspace_id"],
                layer_id=c.get("layer_id", "default"),
                access_roles=c.get("access_roles", []),
                visibility=c.get("visibility", "private"),
                metadata=c["metadata"],
                # Let created_at default or use provided
                created_at=c.get("created_at") or datetime.utcnow().isoformat(),
            ))
            
        # Call synchronous add_chunks
        return self.add_chunks(vector_chunks, workspace_id)
    
    @trace_span("vector_store.add_chunks")
    def add_chunks(self, chunks: List[VectorChunk], workspace_id: str) -> int:
        """
        Add chunks to the vector store with optimized bulk insertion.
        
        Performance optimizations:
        - Direct PyArrow table construction (zero-copy)
        - Single bulk insert (avoids small file problem)
        - Automatic compaction for large inserts
        """
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not chunks:
            return 0
        
        table = self._ensure_table(workspace_id)
        
        # =====================================================================
        # HIGH-PERFORMANCE: Build PyArrow Table directly
        # This bypasses the dict->JSON->Arrow conversion overhead
        # =====================================================================
        
        # Pre-allocate lists for columnar data
        ids = []
        contents = []
        embeddings = []
        document_ids = []
        workspace_ids = []
        layer_ids = []
        access_roles_list = []
        visibilities = []
        metadata_strs = []
        created_ats = []
        
        for chunk in chunks:
            ids.append(chunk.id)
            contents.append(chunk.content)
            embeddings.append(chunk.embedding)
            document_ids.append(chunk.document_id)
            workspace_ids.append(chunk.workspace_id)
            layer_ids.append(chunk.layer_id)
            access_roles_list.append(chunk.access_roles or [])
            visibilities.append(chunk.visibility)
            metadata_strs.append(json.dumps(chunk.metadata) if chunk.metadata else "{}")
            created_ats.append(chunk.created_at)
        
        # Build PyArrow table directly (zero-copy optimization)
        arrow_table = pa.table({
            "id": ids,
            "content": contents,
            "embedding": embeddings,
            "document_id": document_ids,
            "workspace_id": workspace_ids,
            "layer_id": layer_ids,
            "access_roles": access_roles_list,
            "visibility": visibilities,
            "metadata": metadata_strs,
            "created_at": created_ats,
        })
        
        # Single bulk insert
        table.add(arrow_table)
        
        logger.info(f"[VectorStore] Bulk inserted {len(chunks)} chunks to {workspace_id}")
        
        # =====================================================================
        # AUTO-COMPACTION: Merge small fragments for query performance
        # Only trigger for large inserts to avoid overhead on small writes
        # =====================================================================
        
        if len(chunks) > 1000:
            try:
                table.compact_files()
                logger.info(f"[VectorStore] Compacted files for {workspace_id}")
            except Exception as e:
                logger.warning(f"[VectorStore] Compaction skipped: {e}")
        
        return len(chunks)
    
    def get_chunk(self, chunk_id: str, workspace_id: str) -> Optional[VectorChunk]:
        """Get a specific chunk by ID."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return None
        
        table = self.db.open_table(table_name)
        
        # Query by ID
        results = table.search().where(f"id = '{chunk_id}'").limit(1).to_list()
        
        if not results:
            return None
        
        import json
        row = results[0]
        return VectorChunk(
            id=row["id"],
            content=row["content"],
            embedding=row["embedding"],
            document_id=row["document_id"],
            workspace_id=row["workspace_id"],
            layer_id=row.get("layer_id", "default"),
            access_roles=row.get("access_roles", []) or [],
            visibility=row.get("visibility", "private"),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
        )
    
    def get_chunks(
        self,
        workspace_id: str,
        document_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> List[VectorChunk]:
        """Get chunks with optional filtering and pagination."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return []
        
        table = self.db.open_table(table_name)
        
        # Build query
        query = table.search()
        
        if document_id:
            query = query.where(f"document_id = '{document_id}'")
        
        # LanceDB doesn't have native offset, so we fetch more and slice
        results = query.limit(offset + limit).to_list()
        results = results[offset:offset + limit]
        
        import json
        chunks = []
        for row in results:
            chunks.append(VectorChunk(
                id=row["id"],
                content=row["content"],
                embedding=row["embedding"],
                document_id=row["document_id"],
                workspace_id=row["workspace_id"],
                layer_id=row.get("layer_id", "default"),
                access_roles=row.get("access_roles", []) or [],
                visibility=row.get("visibility", "private"),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            ))
        
        return chunks
    
    def update_chunk(
        self,
        chunk_id: str,
        workspace_id: str,
        content: str,
        embedding: List[float],
    ) -> bool:
        """Update a chunk's content and embedding."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return False
        
        table = self.db.open_table(table_name)
        
        # LanceDB update: delete and re-add
        # First get the existing chunk
        existing = self.get_chunk(chunk_id, workspace_id)
        if not existing:
            return False
        
        # Delete old
        table.delete(f"id = '{chunk_id}'")
        
        # Add updated
        import json
        table.add([{
            "id": chunk_id,
            "content": content,
            "embedding": embedding,
            "document_id": existing.document_id,
            "workspace_id": workspace_id,
            "metadata": json.dumps(existing.metadata),
            "created_at": existing.created_at,
        }])
        
        return True
    
    def delete_chunk(self, chunk_id: str, workspace_id: str) -> bool:
        """Delete a specific chunk."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return False
        
        table = self.db.open_table(table_name)
        table.delete(f"id = '{chunk_id}'")
        return True
    
    def delete_document_chunks(self, document_id: str, workspace_id: str) -> int:
        """Delete all chunks for a document."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return 0
        
        table = self.db.open_table(table_name)
        
        # Count before delete
        count_before = table.count_rows()
        
        table.delete(f"document_id = '{document_id}'")
        
        count_after = table.count_rows()
        return count_before - count_after
    
    # ========================================
    # Similarity Search
    # ========================================
    
    @trace_span("vector_store.search")
    def search(
        self,
        query_embedding: List[float],
        workspace_id: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        allowed_layers: List[str] = None, # New Security Filter
    ) -> List[SearchResult]:
        """Search for similar chunks."""
        table_name = self._get_table_name(workspace_id)
        
        if table_name not in self.db.table_names():
            return []
        
        table = self.db.open_table(table_name)
        
        # Build search query - must specify vector column name explicitly
        # Build search query - must specify vector column name explicitly
        # Also convert list to numpy array as LanceDB requires
        import numpy as np
        import logging
        logger = logging.getLogger("uvicorn.error")
        
        query_vector = np.array(query_embedding, dtype=np.float32)
        logger.info(f"DEBUG: query_vector type: {type(query_vector)}, shape: {query_vector.shape}, dtype: {query_vector.dtype}")
        logger.info(f"DEBUG: table name: {table_name}")
        try:
             logger.info(f"DEBUG: table schema: {str(table.schema)}")
        except:
             logger.info("DEBUG: could not print schema")

        logger.info("DEBUG: Executing table.search()")
        query = table.search(query_vector, vector_column_name="embedding")
        
        where_clauses = []
        
        # 1. Security Filter (Mandatory)
        if allowed_layers:
            # Construct SQL-like IN clause: layer_id IN ('a', 'b')
            layers_str = ", ".join([f"'{l}'" for l in allowed_layers])
            where_clauses.append(f"layer_id IN ({layers_str})")
        else:
            # Fallback: If no allowed_layers provided, allow default only (or deny all?)
            # Safer to default to public/default
            where_clauses.append("layer_id IN ('default', 'public')")
            
        # 2. Document Filter
        if document_ids:
            doc_filter = ", ".join([f"'{d}'" for d in document_ids])
            where_clauses.append(f"document_id IN ({doc_filter})")
            
        # Apply Filters with Pre-filtering (Critical for Vector Search)
        if where_clauses:
            full_filter = " AND ".join(where_clauses)
            query = query.where(full_filter, prefilter=True)
        
        logger.info(f"DEBUG: Converting query to list with limit={top_k}")
        results = query.limit(top_k).to_list()
        logger.info(f"DEBUG: Query execution complete, found {len(results)} raw results")
        
        import json
        search_results = []
        for row in results:
            chunk = VectorChunk(
                id=row["id"],
                content=row["content"],
                embedding=row["embedding"],
                document_id=row["document_id"],
                workspace_id=row["workspace_id"],
                layer_id=row.get("layer_id", "default"),
                access_roles=row.get("access_roles", []) or [],
                visibility=row.get("visibility", "private"),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=row["created_at"],
            )
            search_results.append(SearchResult(
                chunk=chunk,
                score=1.0 - row.get("_distance", 0),  # Convert distance to score
                distance=row.get("_distance", 0),
            ))
        
        logger.info(f"DEBUG: Vector search returning {len(search_results)} results")
        return search_results
    
    # ========================================
    # Utility Methods
    # ========================================
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        total_chunks = 0
        total_collections = 0
        total_storage = 0
        
        for table_name in self.db.table_names():
            if table_name.startswith("vectors_"):
                total_collections += 1
                table = self.db.open_table(table_name)
                try:
                    total_chunks += table.count_rows()
                except Exception:
                    pass
        
        # Get total storage
        if os.path.exists(self.db_path):
            for root, dirs, files in os.walk(self.db_path):
                for f in files:
                    total_storage += os.path.getsize(os.path.join(root, f))
        
        return {
            "total_collections": total_collections,
            "total_chunks": total_chunks,
            "total_storage_bytes": total_storage,
            "embedding_dimensions": 1536,
            "database_path": self.db_path,
        }

    def get_layer_distribution(self) -> Dict[str, int]:
        """
        Get distribution of vectors across Knowledge Layers.
        Aggregates counts from all tables.
        """
        layer_counts = {}
        
        for table_name in self.db.table_names():
            if table_name.startswith("vectors_"):
                try:
                    table = self.db.open_table(table_name)
                    # Use LanceDB to query layer_ids
                    # Since we can't easily group by in basic lancedb without loading,
                    # we will limit this to a sample or just count total for now if too expensive.
                    # HOWEVER, for Phase 4 verification, let's try to do it properly if possible.
                    # With pandas:
                    df = table.to_pandas()
                    if "layer_id" in df.columns:
                        counts = df["layer_id"].value_counts().to_dict()
                        for layer, count in counts.items():
                            layer_counts[layer] = layer_counts.get(layer, 0) + count
                except Exception:
                    pass
                    
        return layer_counts
        


# Singleton instance
_vector_store: Optional[LanceDBStore] = None


def get_vector_store() -> LanceDBStore:
    """Get or create the LanceDB vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = LanceDBStore()
    return _vector_store
