"""
GraphRAG Endpoints (Neo4j)
Knowledge graph construction and querying
"""
from typing import List, Optional
from enum import Enum
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.graphrag import get_graph_store, Entity, Relationship, Community

router = APIRouter()


class SearchType(str, Enum):
    """Type of graph search."""
    LOCAL = "local"
    GLOBAL = "global"


# ========================================
# Response Models
# ========================================

class EntityResponse(BaseModel):
    """A knowledge graph entity."""
    id: str
    name: str
    type: str
    description: str
    source_documents: List[str]


class RelationshipResponse(BaseModel):
    """A relationship between entities."""
    id: str
    source_id: str
    target_id: str
    type: str
    description: str


class CommunityResponse(BaseModel):
    """A detected community in the graph."""
    id: str
    level: int
    title: str
    summary: str
    entity_count: int
    key_entities: List[str]


class GraphIndexRequest(BaseModel):
    """Request to index documents into the graph."""
    document_ids: List[str]
    workspace_id: str
    force_reindex: bool = False


class GraphIndexStatus(BaseModel):
    """Status of a graph indexing job."""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float  # 0.0 to 1.0
    entities_extracted: int
    relationships_extracted: int
    communities_detected: int
    error: Optional[str] = None


class GraphQueryRequest(BaseModel):
    """Request for graph query."""
    query: str
    workspace_id: str
    search_type: SearchType = SearchType.LOCAL
    top_k: int = 10


class GraphQueryResponse(BaseModel):
    """Response from graph query."""
    query: str
    search_type: SearchType
    context: str
    entities: List[EntityResponse]
    relationships: List[RelationshipResponse]
    communities: List[CommunityResponse]


# ========================================
# Endpoints
# ========================================

@router.post("/index")
async def start_graph_indexing(request: GraphIndexRequest) -> dict:
    """
    Trigger GraphRAG indexing for documents.

    This queues a Celery job that:
    1. Extracts entities using LLM
    2. Extracts relationships
    3. Runs community detection (Leiden algorithm)
    4. Stores results in Neo4j
    """
    try:
        from app.workers.tasks.indexing import start_graph_indexing as indexing_task
        result = indexing_task.delay(request.document_ids, request.workspace_id)
        return {
            "status": "queued",
            "job_id": result.id,
            "document_count": len(request.document_ids),
            "workspace_id": request.workspace_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to queue indexing job: {e}",
            "workspace_id": request.workspace_id,
        }


@router.get("/status/{job_id}", response_model=GraphIndexStatus)
async def get_indexing_status(job_id: str) -> GraphIndexStatus:
    """Check the status of a graph indexing job."""
    try:
        from app.workers.celery_app import celery_app
        result = celery_app.AsyncResult(job_id)

        status_map = {
            "PENDING": "pending",
            "STARTED": "running",
            "PROGRESS": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "REVOKED": "cancelled",
        }

        status = status_map.get(result.status, "unknown")

        # Get progress info if available
        info = result.info if result.info else {}
        if isinstance(info, Exception):
            info = {"error": str(info)}

        return GraphIndexStatus(
            job_id=job_id,
            status=status,
            progress=info.get("progress", 0.0),
            entities_extracted=info.get("entities_extracted", 0),
            relationships_extracted=info.get("relationships_extracted", 0),
            communities_detected=info.get("communities_detected", 0),
            error=info.get("error"),
        )
    except Exception:
        return GraphIndexStatus(
            job_id=job_id,
            status="unknown",
            progress=0.0,
            entities_extracted=0,
            relationships_extracted=0,
            communities_detected=0,
        )


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(request: GraphQueryRequest) -> GraphQueryResponse:
    """
    Execute a GraphRAG query.

    - LOCAL: Find relevant entities and their immediate context
    - GLOBAL: Query community summaries for high-level themes
    """
    graph_store = get_graph_store()

    # Check connectivity
    if not graph_store.verify_connectivity():
        raise HTTPException(status_code=503, detail="Neo4j database unavailable")

    if request.search_type == SearchType.GLOBAL:
        # Global search - query communities
        result = graph_store.global_search(
            workspace_id=request.workspace_id,
            top_communities=request.top_k,
        )

        return GraphQueryResponse(
            query=request.query,
            search_type=request.search_type,
            context=result.get("context", ""),
            entities=[],
            relationships=[],
            communities=[
                CommunityResponse(
                    id=c.id,
                    level=c.level,
                    title=c.title,
                    summary=c.summary,
                    entity_count=len(c.entity_ids),
                    key_entities=c.entity_ids[:5],
                )
                for c in result.get("communities", [])
            ],
        )
    else:
        # Local search - find relevant entities
        # For now, use query as entity name (would use NER/LLM in production)
        result = graph_store.local_search(
            query_entities=[request.query],
            workspace_id=request.workspace_id,
            hops=2,
            limit=request.top_k,
        )

        # Build context from entities
        entities = result.get("entities", [])
        context_parts = [f"- {e.name}: {e.description}" for e in entities[:10]]
        context = "\n".join(context_parts)

        return GraphQueryResponse(
            query=request.query,
            search_type=request.search_type,
            context=context,
            entities=[
                EntityResponse(
                    id=e.id,
                    name=e.name,
                    type=e.type,
                    description=e.description,
                    source_documents=e.source_documents,
                )
                for e in entities
            ],
            relationships=[
                RelationshipResponse(
                    id=r.id,
                    source_id=r.source_id,
                    target_id=r.target_id,
                    type=r.type,
                    description=r.description,
                )
                for r in result.get("relationships", [])
            ],
            communities=[],
        )


@router.get("/entities/{workspace_id}", response_model=List[EntityResponse])
async def list_entities(
    workspace_id: str,
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=500),
) -> List[EntityResponse]:
    """List entities in the knowledge graph."""
    graph_store = get_graph_store()

    entities = graph_store.get_entities(
        workspace_id=workspace_id,
        entity_type=entity_type,
        limit=limit,
    )

    return [
        EntityResponse(
            id=e.id,
            name=e.name,
            type=e.type,
            description=e.description,
            source_documents=e.source_documents,
        )
        for e in entities
    ]


@router.get("/relationships/{workspace_id}", response_model=List[RelationshipResponse])
async def list_relationships(
    workspace_id: str,
    source_id: Optional[str] = None,
    target_id: Optional[str] = None,
    limit: int = Query(100, le=500),
) -> List[RelationshipResponse]:
    """List relationships in the knowledge graph."""
    graph_store = get_graph_store()

    relationships = graph_store.get_relationships(
        workspace_id=workspace_id,
        source_id=source_id,
        target_id=target_id,
        limit=limit,
    )

    return [
        RelationshipResponse(
            id=r.id,
            source_id=r.source_id,
            target_id=r.target_id,
            type=r.type,
            description=r.description,
        )
        for r in relationships
    ]


@router.get("/communities/{workspace_id}", response_model=List[CommunityResponse])
async def list_communities(
    workspace_id: str,
    level: Optional[int] = None,
) -> List[CommunityResponse]:
    """List detected communities in the graph."""
    graph_store = get_graph_store()

    communities = graph_store.get_communities(
        workspace_id=workspace_id,
        level=level,
    )

    return [
        CommunityResponse(
            id=c.id,
            level=c.level,
            title=c.title,
            summary=c.summary,
            entity_count=len(c.entity_ids),
            key_entities=c.entity_ids[:5],
        )
        for c in communities
    ]


@router.get("/stats/{workspace_id}")
async def get_graph_stats(workspace_id: str) -> dict:
    """Get graph statistics for a workspace."""
    graph_store = get_graph_store()

    try:
        stats = graph_store.get_stats(workspace_id)
        return {
            **stats,
            "workspace_id": workspace_id,
            "last_indexed": None,  # Would come from job tracking
        }
    except Exception as e:
        return {
            "entity_count": 0,
            "relationship_count": 0,
            "community_count": 0,
            "entity_types": [],
            "workspace_id": workspace_id,
            "error": str(e),
        }


@router.delete("/workspace/{workspace_id}")
async def clear_workspace_graph(workspace_id: str) -> dict:
    """Clear all graph data for a workspace."""
    graph_store = get_graph_store()

    try:
        graph_store.clear_workspace(workspace_id)
        return {"workspace_id": workspace_id, "status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear workspace: {e}")


@router.get("/health")
async def graph_health() -> dict:
    """Check Neo4j connectivity."""
    graph_store = get_graph_store()

    connected = graph_store.verify_connectivity()

    return {
        "status": "healthy" if connected else "unhealthy",
        "neo4j_connected": connected,
    }
