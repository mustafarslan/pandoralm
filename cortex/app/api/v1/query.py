"""
Query Endpoints
Hybrid RAG query routing (Vector + Graph)
"""
from typing import List, Optional
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.services.graphrag import get_query_router, QueryMode
from app.auth.keycloak import verifier
from app.services.audit_service import audit_log_background

router = APIRouter()


class QueryModeEnum(str, Enum):
    """Query mode options."""
    auto = "auto"
    vector = "vector"
    graph = "graph"
    hybrid = "hybrid"
    research = "research"


class QueryRequest(BaseModel):
    """Hybrid query request."""
    query: str
    workspace_id: str
    mode: QueryModeEnum = QueryModeEnum.auto
    top_k: int = 10
    document_ids: Optional[List[str]] = None


class SourceItem(BaseModel):
    """A source document/chunk."""
    chunk_id: str
    document_id: str
    content: str
    score: float


class EntityItem(BaseModel):
    """An entity from the knowledge graph."""
    id: str
    name: str
    type: str
    description: str


class CommunityItem(BaseModel):
    """A community from the knowledge graph."""
    id: str
    title: str
    summary: str
    entity_count: int



class QueryMetadata(BaseModel):
    """Metadata for query execution."""
    router_decision: str
    latency_ms: float
    retrieved_context: List[str]


class QueryResponse(BaseModel):
    """Hybrid query response."""
    answer: str
    metadata: QueryMetadata
    sources: List[SourceItem]
    entities: List[EntityItem]
    communities: List[CommunityItem]
    confidence: float


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    token_payload: dict = Depends(verifier.verify_token)
) -> QueryResponse:
    """
    Execute a hybrid RAG query.

    Modes:
    - **auto**: Automatically detect best search type
    - **vector**: Semantic similarity search (LanceDB)
    - **graph**: Knowledge graph traversal (Neo4j)
    - **hybrid**: Combined vector + graph search
    """
    # Authorization: Resolve Knowledge Layers (RBAC)
    user_id = token_payload.get("sub") or token_payload.get("preferred_username")
    realm_roles = token_payload.get("realm_access", {}).get("roles", [])

    # 1. Base Layer: Default/Public
    allowed_layers = ["default", "public"]

    # 2. User Layer: Private data
    if user_id:
        allowed_layers.append(user_id)

    # 3. Role-Based Layers: Map Keycloak groups to layers
    # e.g. "group:engineering" -> "layer_engineering"
    for role in realm_roles:
        if role.startswith("group:"):
            # Normalize group name to layer ID convention
            layer_name = role.replace("group:", "layer_")
            allowed_layers.append(layer_name)

    # Admin Override: Can see everything (or specific admin layers)
    if "admin" in realm_roles or "vector_ops" in realm_roles:
        # In a real system, you might fetch ALL layers, or use a wildcard logic
        # For this implementation, we assume admin has explicit access to sensitive layers
        allowed_layers.extend(["restricted", "admin"])

    query_router = get_query_router()

    # Map request mode to internal QueryMode
    mode_map = {
        QueryModeEnum.auto: QueryMode.AUTO,
        QueryModeEnum.vector: QueryMode.VECTOR,
        QueryModeEnum.graph: QueryMode.GRAPH,
        QueryModeEnum.hybrid: QueryMode.HYBRID,
    }

    mode = mode_map[request.mode]

    # Audit Log (Background Task)
    background_tasks.add_task(
        audit_log_background,
        user_id=str(user_id) if user_id else "anonymous",
        workspace_id=request.workspace_id,
        action="query",
        details={
            "query": request.query,
            "mode": request.mode,
            "top_k": request.top_k
        }
    )

    try:
        result = await query_router.route_query(
            query=request.query,
            workspace_id=request.workspace_id,
            mode=mode,
            top_k=request.top_k,
            document_ids=request.document_ids,
            allowed_layers=allowed_layers, # Pass Security Context
        )

        # Extract plain text context for evaluation
        retrieved_context = [s["content"] for s in result.sources]

        return QueryResponse(
            answer=result.content,  # Renamed from context to answer for clarity
            metadata=QueryMetadata(
                router_decision=result.mode.value,
                latency_ms=getattr(result, "classification_latency_ms", 0.0) or 0.0, # Handle optional latency
                retrieved_context=retrieved_context,
            ),
            sources=[
                SourceItem(
                    chunk_id=s["chunk_id"],
                    document_id=s["document_id"],
                    content=s["content"],
                    score=s["score"],
                )
                for s in result.sources
            ],
            entities=[
                EntityItem(
                    id=e["id"],
                    name=e["name"],
                    type=e["type"],
                    description=e["description"],
                )
                for e in result.entities
            ],
            communities=[
                CommunityItem(
                    id=c["id"],
                    title=c["title"],
                    summary=c["summary"],
                    entity_count=c["entity_count"],
                )
                for c in result.communities
            ],
            confidence=result.confidence,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/modes")
async def list_query_modes() -> dict:
    """List available query modes with descriptions."""
    return {
        "modes": [
            {
                "id": "auto",
                "name": "Auto-Detect",
                "description": "Automatically determine best search type based on query",
            },
            {
                "id": "vector",
                "name": "Vector Search",
                "description": "Semantic similarity search - best for specific facts and similar content",
            },
            {
                "id": "graph",
                "name": "Graph Search",
                "description": "Knowledge graph traversal - best for relationships and themes",
            },
            {
                "id": "hybrid",
                "name": "Hybrid Search",
                "description": "Combined vector + graph - comprehensive context for complex questions",
            },
        ]
    }
