"""
Vector Operations Endpoints (LanceDB)
Port of Vector-Admin functionality
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.services import get_vector_store, get_embedding_service


print("DEBUG: LOADED VECTOR_STORE.PY MODULE", flush=True)

router = APIRouter()


# ========================================
# Request/Response Models
# ========================================

class VectorChunkResponse(BaseModel):
    """A vector chunk with metadata."""
    id: str
    content: str
    embedding_preview: List[float]  # First 5 dimensions
    document_id: str
    workspace_id: str
    metadata: dict
    created_at: str


class ChunkUpdateRequest(BaseModel):
    """Request to update a chunk."""
    content: str
    re_embed: bool = True


class CollectionStatsResponse(BaseModel):
    """Statistics for a vector collection."""
    name: str
    workspace_id: str
    total_chunks: int
    dimensions: int
    storage_bytes: int
    exists: bool


class PaginatedChunksResponse(BaseModel):
    """Paginated response of chunks."""
    chunks: List[VectorChunkResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    workspace_id: str
    top_k: int = 10
    document_ids: Optional[List[str]] = None
    allowed_layers: Optional[List[str]] = None


class SearchResultResponse(BaseModel):
    """Search result item."""
    chunk: VectorChunkResponse
    score: float
    distance: float


# ========================================
# Endpoints
# ========================================

@router.get("/collections", response_model=List[CollectionStatsResponse])
async def list_collections() -> List[CollectionStatsResponse]:
    """List all LanceDB collections (tables)."""
    vector_store = get_vector_store()
    collections = vector_store.list_collections()
    
    return [
        CollectionStatsResponse(
            name=c["name"],
            workspace_id=c["workspace_id"],
            total_chunks=c["total_chunks"],
            dimensions=c["dimensions"],
            storage_bytes=0,
            exists=True,
        )
        for c in collections
    ]


@router.get("/collections/{workspace_id}", response_model=CollectionStatsResponse)
async def get_collection_stats(workspace_id: str) -> CollectionStatsResponse:
    """Get detailed stats for a specific collection."""
    vector_store = get_vector_store()
    stats = vector_store.get_collection_stats(workspace_id)
    
    return CollectionStatsResponse(
        name=stats["name"],
        workspace_id=stats["workspace_id"],
        total_chunks=stats["total_chunks"],
        dimensions=stats["dimensions"],
        storage_bytes=stats["storage_bytes"],
        exists=stats["exists"],
    )


@router.get("/collections/{workspace_id}/chunks", response_model=PaginatedChunksResponse)
async def get_collection_chunks(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    document_id: Optional[str] = None,
) -> PaginatedChunksResponse:
    """
    Get chunks in a collection with pagination.
    
    Optionally filter by document_id.
    """
    vector_store = get_vector_store()
    
    offset = (page - 1) * page_size
    chunks = vector_store.get_chunks(
        workspace_id=workspace_id,
        document_id=document_id,
        offset=offset,
        limit=page_size + 1,  # Extra to check if more
    )
    
    has_more = len(chunks) > page_size
    if has_more:
        chunks = chunks[:page_size]
    
    # Get total count
    stats = vector_store.get_collection_stats(workspace_id)
    
    return PaginatedChunksResponse(
        chunks=[
            VectorChunkResponse(
                id=c.id,
                content=c.content,
                embedding_preview=c.embedding[:5] if c.embedding else [],
                document_id=c.document_id,
                workspace_id=c.workspace_id,
                metadata=c.metadata,
                created_at=c.created_at,
            )
            for c in chunks
        ],
        total=stats["total_chunks"],
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/chunks/{workspace_id}/{chunk_id}", response_model=VectorChunkResponse)
async def get_chunk(workspace_id: str, chunk_id: str) -> VectorChunkResponse:
    """Get a specific chunk by ID."""
    vector_store = get_vector_store()
    chunk = vector_store.get_chunk(chunk_id, workspace_id)
    
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return VectorChunkResponse(
        id=chunk.id,
        content=chunk.content,
        embedding_preview=chunk.embedding[:5] if chunk.embedding else [],
        document_id=chunk.document_id,
        workspace_id=chunk.workspace_id,
        metadata=chunk.metadata,
        created_at=chunk.created_at,
    )


@router.put("/chunks/{workspace_id}/{chunk_id}", response_model=VectorChunkResponse)
async def update_chunk(
    workspace_id: str,
    chunk_id: str,
    update: ChunkUpdateRequest,
) -> VectorChunkResponse:
    """
    Update a chunk's content.
    
    If re_embed is True (default), regenerates the embedding vector.
    """
    vector_store = get_vector_store()
    
    # Check chunk exists
    existing = vector_store.get_chunk(chunk_id, workspace_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    # Generate new embedding if needed
    if update.re_embed:
        embedding_service = get_embedding_service()
        result = await embedding_service.embed_text(update.content)
        embedding = result.embedding
    else:
        embedding = existing.embedding
    
    # Update chunk
    updated_chunk = vector_store.update_chunk(
        chunk_id=chunk_id,
        workspace_id=workspace_id,
        content=update.content,
        embedding=embedding,
    )
    
    if not updated_chunk:
        raise HTTPException(status_code=500, detail="Failed to update chunk")
    
    # Return updated chunk
    return VectorChunkResponse(
        id=updated_chunk.id,
        content=updated_chunk.content,
        embedding_preview=updated_chunk.embedding[:5] if updated_chunk.embedding else [],
        document_id=updated_chunk.document_id,
        workspace_id=updated_chunk.workspace_id,
        metadata=updated_chunk.metadata,
        created_at=updated_chunk.created_at,
    )


@router.delete("/chunks/{workspace_id}/{chunk_id}")
async def delete_chunk(workspace_id: str, chunk_id: str) -> dict:
    """Delete a specific chunk."""
    vector_store = get_vector_store()
    
    success = vector_store.delete_chunk(chunk_id, workspace_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return {"deleted": chunk_id, "workspace_id": workspace_id}


@router.delete("/documents/{workspace_id}/{document_id}")
async def delete_document_chunks(workspace_id: str, document_id: str) -> dict:
    """Delete all chunks for a document."""
    vector_store = get_vector_store()
    
    deleted_count = vector_store.delete_document_chunks(document_id, workspace_id)
    
    return {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "deleted_chunks": deleted_count,
    }


@router.post("/collections/{workspace_id}/reindex")
async def reindex_collection(workspace_id: str) -> dict:
    """
    Trigger full reindex of a collection.
    
    This queues a Celery job for background processing.
    """
    try:
        from app.workers.tasks.indexing import reindex_vectors
        result = reindex_vectors.delay(workspace_id)
        return {
            "status": "queued",
            "workspace_id": workspace_id,
            "job_id": result.id,
        }
    except Exception as e:
        # Celery not available
        return {
            "status": "error",
            "workspace_id": workspace_id,
            "message": f"Background processing unavailable: {e}",
        }


@router.delete("/collections/{workspace_id}")
async def delete_collection(workspace_id: str) -> dict:
    """Delete an entire collection (Vectors + Graph)."""
    vector_store = get_vector_store()
    
    # 1. Delete Vectors (LanceDB)
    success = vector_store.delete_collection(workspace_id)
    
    # 2. Delete Graph (Neo4j)
    try:
        from app.services.graphrag import get_graph_store
        graph_store = get_graph_store()
        graph_store.clear_workspace(workspace_id)
        # Even if vector store had no table (already deleted), we should ensure graph is clean
        success = True 
    except Exception as e:
        print(f"Error clearing graph for workspace {workspace_id}: {e}", flush=True)
        # Don't fail the request if graph delete fails, but log it
    
    if not success:
        # If both failed (e.g. neither existed), then 404
        # But for now, if vectors succeed or graph succeeds, we return success
        pass

    return {"deleted": workspace_id, "status": "deleted"}


@router.post("/search", response_model=List[SearchResultResponse])
async def semantic_search(request: SearchRequest) -> List[SearchResultResponse]:
    """
    Perform semantic search across vectors.
    
    Generates embedding for query and finds similar chunks.
    """
    print(f"DEBUG: Search request for '{request.query[:50]}...' in {request.workspace_id}", flush=True)
    
    # Generate query embedding
    embedding_service = get_embedding_service()
    result = await embedding_service.embed_text(request.query)
    
    print("DEBUG: Embedding generated", flush=True)
    
    # Search
    vector_store = get_vector_store()
    results = vector_store.search(
        query_embedding=result.embedding,
        workspace_id=request.workspace_id,
        top_k=request.top_k,
        document_ids=request.document_ids,
        # allowed_layers=request.allowed_layers # Not yet supported in vector_store, but model accepts it
    )
    
    print(f"DEBUG: Found {len(results)} results", flush=True)
    
    return [
        SearchResultResponse(
            chunk=VectorChunkResponse(
                id=r.chunk.id,
                content=r.chunk.content,
                embedding_preview=r.chunk.embedding[:5] if r.chunk.embedding else [],
                document_id=r.chunk.document_id,
                workspace_id=r.chunk.workspace_id,
                metadata=r.chunk.metadata,
                created_at=r.chunk.created_at,
            ),
            score=r.score,
            distance=r.distance,
        )
        for r in results
    ]


@router.get("/stats")
async def get_vector_stats() -> dict:
    """Get overall vector database statistics."""
    vector_store = get_vector_store()
    return vector_store.get_total_stats()
