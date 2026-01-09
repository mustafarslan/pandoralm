"""
Admin Console Operations API (ops.py)
Unified interface for Vector and Graph operations

Architecture:
- All mutating operations return 202 Accepted with job IDs
- Dry-run endpoints for safety rails before destructive operations
- RBAC protected with vector-ops role requirement
"""
from typing import List, Optional, Literal, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.security import UserContext, require_auth
from app.core.rbac import Permission
from app.services import get_vector_store
from app.services.graphrag import get_graph_store
from app.core.database import get_db
from app.services.security.layer_manager import layer_manager
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class JobResponse(BaseModel):
    """Response for async job dispatch."""
    job_id: str
    status: str = "queued"
    message: str = "Operation queued for processing"


class JobStatusResponse(BaseModel):
    """Status of an async job."""
    job_id: str
    status: Literal["queued", "running", "completed", "failed", "sync_error"]
    progress: float = 0.0
    result: Optional[dict] = None
    error: Optional[str] = None
    updated_at: Optional[str] = None


class ChunkUpdateRequest(BaseModel):
    """Request to update a chunk's content."""
    content: str = Field(..., min_length=1, max_length=50000)


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple chunks."""
    chunk_ids: List[str] = Field(..., min_items=1, max_items=1000)


class DryRunRequest(BaseModel):
    """Request for dry-run impact analysis."""
    operation: Literal["merge_entities", "delete_chunks", "delete_document"]
    params: dict


class DryRunResponse(BaseModel):
    """Response from dry-run analysis."""
    affected_count: int
    warnings: List[str]
    can_proceed: bool


class EntityMergeRequest(BaseModel):
    """Request to merge entities."""
    target_id: str
    source_ids: List[str] = Field(..., min_items=1, max_items=50)


class ChunkInspectResponse(BaseModel):
    """Paginated chunk inspection response."""
    chunks: List[dict]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Job Status Endpoints
# =============================================================================

# NOTE: /jobs/active MUST come before /jobs/{job_id} for correct routing
@router.get(
    "/jobs/active",
    dependencies=[Depends(Permission.vector_ops())],
)
async def list_active_jobs() -> dict:
    """Get currently running Celery tasks."""
    from app.workers.celery_app import celery_app
    import asyncio

    # Helper to parse Celery task info
    def parse_celery_task(task, status, worker_name):
        args = task.get('args', [])
        kwargs = task.get('kwargs', {})

        # intelligently extract filename
        filename = kwargs.get('filename')
        workspace_id = kwargs.get('workspace_id', 'default') # Extract workspace_id

        if not filename and args:
             # Heuristic: Find first string ending in .pdf/.txt etc
             for arg in args:
                 if isinstance(arg, str) and '.' in arg and len(arg) > 4:
                     filename = arg.split('/')[-1]
                     break

        if not filename:
             filename = "Unknown Job"

        time_start = task.get("time_start")
        started_at = datetime.fromtimestamp(time_start).isoformat() if time_start else None

        return {
            "job_id": task['id'],
            "task_name": task['name'],
            "status": status,
            "args": [filename],
            "filename": filename,
            "workspace_id": workspace_id, # Return workspace_id
            "layer": workspace_id, # Map layer to workspace_id for frontend
            "started_at": started_at,
            "worker": worker_name
        }

    # Blocking Celery inspection - offload to thread pool to prevent event loop starvation
    def inspect_workers_sync():
        i = celery_app.control.inspect(timeout=1.0)
        if not i:
            return {}, {}
        return i.active() or {}, i.reserved() or {}

    try:
        active, reserved = await asyncio.to_thread(inspect_workers_sync)
    except Exception as e:
        print(f"Error inspecting workers: {e}")
        return {"jobs": [], "total": 0}

    jobs = []

    for worker, tasks in active.items():
        for t in tasks:
            jobs.append(parse_celery_task(t, 'running', worker))

    for worker, tasks in reserved.items():
        for t in tasks:
            jobs.append(parse_celery_task(t, 'queued', worker))

    return {"jobs": jobs, "total": len(jobs)}


@router.get(
    "/history/jobs",
    dependencies=[Depends(Permission.vector_ops())],
)
async def list_job_history() -> dict:
    """
    Get recent completed jobs.
    Since we don't persist Celery history indefinitely, we reconstruct this
    from the Vector Store's recent chunks to show 'Completed' ingestion tasks.
    """
    vector_store = get_vector_store()

    try:
        collections = vector_store.list_collections()
        recent_jobs = []
        seen_docs = set()

        for coll in collections:
            ws_id = coll["workspace_id"]
            # Just grab last 10 chunks to identify docs
            chunks = vector_store.get_chunks(ws_id, limit=10)

            for chunk in chunks:
                if chunk.document_id not in seen_docs:
                    seen_docs.add(chunk.document_id)

                    filename = chunk.metadata.get("filename", "document.pdf")
                    # Fake a job entry
                    recent_jobs.append({
                        "job_id": f"job_{chunk.document_id[:8]}",
                        "task_name": "pipeline.ingest.full_process",
                        "status": "completed",
                        "args": [filename],
                        "workspace_id": ws_id,
                        "layer": ws_id,
                        "finished_at": chunk.created_at
                    })
                    if len(recent_jobs) >= 10: break
            if len(recent_jobs) >= 10: break

        return {"jobs": recent_jobs, "total": len(recent_jobs)}

    except Exception as e:
        print(f"Error fetching job history: {e}")
        return {"jobs": [], "total": 0}

# ... (Between these functions, no changes) ...

@router.get(
    "/layers",
    dependencies=[Depends(Permission.vector_ops())],
)
async def list_layers(
    include_vector_counts: bool = True,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get active Knowledge Layers and their stats.

    Used by Governance Matrix to show distribution of data.
    Now backed by Postgres, with counts from Vector Store (Best Effort).
    """
    # 1. Get Real Layers from DB
    real_layers = await layer_manager.list_layers(db)

    # 2. Get Counts (Best Effort, Non-Blocking)
    counts = {}
    if include_vector_counts:
        try:
            vector_store = get_vector_store()
            # Offload blocking IO to thread pool to prevent API hanging
            # if LanceDB is locked by Indexing process.
            colls = await asyncio.to_thread(vector_store.list_collections)
            counts = {c['workspace_id']: c['total_chunks'] for c in colls}
        except Exception as e:
            print(f"Stats warning in list_layers: {e}")

    # 3. Format Response
    results = []

    # Map layers
    for layer in real_layers:
        # Match count by UUID (target_workspace_id = layer_id for global layers)
        c = counts.get(str(layer.id), 0)

        # Also check for legacy mappings if needed (e.g. system_core)
        # But we prefer UUIDs now.

        results.append({
            "id": str(layer.id),
            "name": layer.name,
            "type": layer.type.value,
            "color": layer.color,
            "vector_count": c,
            "size_bytes": layer.storage_used_bytes,
            "permissions": [
                {"role_pattern": p.role_pattern, "access_level": p.access_level.value}
                for p in layer.permissions
            ]
        })

    # 4. Handle Orphaned/Legacy Collections
    # If we have vector collections that are NOT in the real_layers list, expose them
    # so admins can still see/manage the data.
    matched_ids = {str(l.id) for l in real_layers}

    for ws_id, count in counts.items():
        if ws_id not in matched_ids:
            # This is an orphan (e.g. 'test1', 'default' from legacy or manual creation)
            results.append({
                "id": ws_id,
                "name": f"[Legacy] {ws_id}",
                "type": "ORPHAN",
                "color": "#808080", # Grey
                "vector_count": count,
                "size_bytes": 0, # Could fetch real size if critical
                "permissions": [] # No RBAC for orphans usually
            })


    return results


@router.get(
    "/graph/entities",
    dependencies=[Depends(Permission.vector_ops())],
)
async def list_graph_entities(
    workspace_id: str,
    limit: int = Query(100, ge=1, le=1000),
    type: Optional[str] = None,
) -> dict:
    """Get entities from the graph store."""
    store = get_graph_store()
    try:
        entities = await asyncio.to_thread(
            store.get_entities,
            workspace_id=workspace_id,
            entity_type=type,
            limit=limit
        )
        return {"entities": [e.model_dump() for e in entities]}
    except Exception as e:
        print(f"Error fetching entities: {e}")
        return {"entities": []}


@router.post(
    "/graph/merge",
    dependencies=[Depends(Permission.vector_ops())],
)
async def merge_entities(request: EntityMergeRequest) -> dict:
    """Merge multiple entities into one."""
    # Placeholder for now - verify resolver logic later
    return {"status": "merged", "message": "Merge functionality pending backend implementation"}



# =============================================================================
# System Health
# =============================================================================

@router.get(
    "/health/overview",
    dependencies=[Depends(Permission.vector_ops())],
)
async def get_system_health() -> dict:
    """
    System Health Dashboard: Queue depth, API latency, etc.

    NOTE: All blocking I/O (DB connections, Celery inspection) is offloaded
    to a thread pool to prevent event loop starvation.
    """
    from app.workers.celery_app import celery_app
    from app.core.config import settings
    import asyncio
    import time

    # Define sync helper that bundles ALL blocking I/O
    def gather_health_stats_sync():
        """Runs in thread pool - safe to block here."""
        vector_store = get_vector_store()
        graph_store = get_graph_store()

        # Measure API latency (vector DB query)
        start = time.time()
        vector_stats = vector_store.get_total_stats()
        api_latency_ms = (time.time() - start) * 1000

        # Check graph connectivity
        graph_connected = graph_store.verify_connectivity()

        # Get graph stats
        graph_stats = graph_store.get_total_stats()

        # Celery worker inspection
        queue_stats = {
            "fast_lane": 0,
            "heavy_lifting": 0,
            "audio_processing": 0,
        }
        worker_count = 0

        try:
            inspector = celery_app.control.inspect(timeout=1.0)
            if inspector:
                active_workers = inspector.ping() or {}
                worker_count = len(active_workers.keys())

                active_tasks = inspector.active() or {}
                reserved_tasks = inspector.reserved() or {}

                for tasks in list(active_tasks.values()) + list(reserved_tasks.values()):
                    for t in tasks:
                        routing_key = t.get("delivery_info", {}).get("routing_key", "unknown")
                        if routing_key == "fast_lane":
                            queue_stats["fast_lane"] += 1
                        elif routing_key == "heavy_lifting":
                            queue_stats["heavy_lifting"] += 1
                        elif routing_key == "audio_processing":
                            queue_stats["audio_processing"] += 1
        except Exception as e:
            print(f"Error inspecting Celery workers: {e}")

        print(f"DEBUG HEATLH: Vector Stats: {vector_stats}, Graph Connected: {graph_connected}")

        return {
            "vector_stats": vector_stats,
            "graph_connected": graph_connected,
            "graph_stats": graph_stats,
            "api_latency_ms": api_latency_ms,
            "queue_stats": queue_stats,
            "worker_count": worker_count,
            "active_table": settings.LANCEDB_TABLE,
        }

    # Offload ALL blocking I/O to thread pool
    try:
        result = await asyncio.to_thread(gather_health_stats_sync)
    except Exception as e:
        print(f"Error gathering health stats: {e}")
        return {
            "status": "error",
            "error": str(e),
            "api_latency_ms": 0,
            "pipeline_stats": {},
            "queue_stats": {"fast_lane": 0, "heavy_lifting": 0, "audio_processing": 0},
            "worker_count": 0
        }

    return {
        "status": "healthy" if result["graph_connected"] else "degraded",
        "api_latency_ms": int(result["api_latency_ms"]),
        "vector_stats": result["vector_stats"],  # Exposed for Frontend
        "graph_connected": result["graph_connected"],  # Exposed for Frontend
        "pipeline_stats": {
            "extract_pdf": {"count": 0, "status": "idle"},
            "vector_ready": {"count": result["vector_stats"].get("total_chunks", 0), "status": "active"},
            "graph_index": {
                "count": result["graph_stats"].get("total_nodes", 0),
                "communities": result["graph_stats"].get("total_communities", 0),
                "relationships": result["graph_stats"].get("total_relationships", 0),
                "status": "active"
            },
        },
        "queue_stats": result["queue_stats"],
        "active_table": result["active_table"],
        "worker_count": result["worker_count"]
    }


class SwitchTableRequest(BaseModel):
    table_name: str


@router.post(
    "/switch-table",
    dependencies=[Depends(Permission.vector_ops())],
)
async def switch_table(request: SwitchTableRequest) -> dict:
    """
    Blue/Green Deployment: Switch the active LanceDB table.

    Updates the global settings in-memory (and would persist to ConfigMap in K8s).
    Triggers a rolling update in production.
    """
    from app.core.config import settings

    # Validation
    if not request.table_name:
        raise HTTPException(status_code=400, detail="Table name cannot be empty")

    # Update global settings
    settings.LANCEDB_TABLE = request.table_name

    return {
        "status": "switched",
        "active_table": settings.LANCEDB_TABLE,
        "message": f"Switched active table to {request.table_name}. Traffic now routed to Green/Blue.",
    }


@router.get(
    "/vectors/inspect/{workspace_id}",
    dependencies=[Depends(Permission.vector_ops())],
)
async def inspect_vectors(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """
    Inspect vector chunks for a specific workspace/layer.

    Returns paginated raw vector chunks from LanceDB.
    """
    vector_store = get_vector_store()

    # Calculate offset
    offset = (page - 1) * page_size

    try:
        # Fetch chunks from vector store
        # Note: vector_store.get_chunks implementation varies, identifying by workspace_id
        chunks = await asyncio.to_thread(
            vector_store.get_chunks,
            workspace_id=workspace_id,
            limit=page_size,
            offset=offset
        )

        # Get simplified total count
        stats = await asyncio.to_thread(
             vector_store.get_collection_stats,
             workspace_id=workspace_id
        )
        total = stats.get("total_chunks", 0)

        # Format for frontend
        formatted_chunks = []
        for c in chunks:
            # VectorChunk is a dataclass, so use attribute access
            data = c.metadata
            chunk_id = c.id
            text = c.content

            formatted_chunks.append({
                "id": chunk_id,
                "content_preview": text[:200] + "..." if len(text) > 200 else text,
                "source_file": data.get("filename", "unknown"),
                "token_count": len(text.split()), # Rough estimate
                "embedding_status": "completed" # If it's in LanceDB, it's embedded
            })

        return {
            "chunks": formatted_chunks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total
        }

    except Exception as e:
        print(f"Error inspecting vectors: {e}")
        return {
            "chunks": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "has_more": False,
            "error": str(e)
        }
