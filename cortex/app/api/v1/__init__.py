"""
API v1 Router
# Reload Triggered: Fix for Evaluation Module Import
"""

from fastapi import APIRouter

from app.api.v1.ingest import router as ingest_router
from app.api.v1.documents import router as documents_router
from app.api.v1.vectors import router as vectors_router
from app.api.v1.graph import router as graph_router
from app.api.v1.research import router as research_router
from app.api.v1.system import router as system_router
from app.api.v1.query import router as query_router
from app.api.v1.visualization import router as viz_router
from app.api.v1.admin import router as admin_router
from app.api.v1.router import router as cognitive_router
from app.api.v1.ops import router as ops_router
from app.api.v1.web import router as web_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin.layers import router as admin_layers_router
from app.api.v1.user_layers import router as user_layers_router
from app.api.v1.legacy import router as legacy_router
from app.api.v1.workspace import router as workspace_router
from app.api.v1.workspace_layers import router as workspace_layers_router
from app.api.v1.audit import router as audit_router

from app.api.v1.stream import router as stream_router

router = APIRouter()

router.include_router(ingest_router, prefix="/ingest", tags=["Ingestion"])
router.include_router(documents_router, prefix="/document", tags=["Documents"])
router.include_router(vectors_router, prefix="/vectors", tags=["Vectors"])
router.include_router(graph_router, prefix="/graph", tags=["Graph"])
router.include_router(query_router, prefix="/query", tags=["Query"])
router.include_router(stream_router, prefix="/stream", tags=["Stream"])
router.include_router(viz_router, prefix="/viz", tags=["Visualization"])
router.include_router(research_router, prefix="/research", tags=["Research"])
router.include_router(system_router, prefix="/system", tags=["System"])
router.include_router(admin_router, prefix="/admin", tags=["Admin"])
router.include_router(cognitive_router, prefix="/router", tags=["Cognitive Router"])
router.include_router(ops_router, prefix="/ops", tags=["Admin Console Operations"])
router.include_router(legacy_router, tags=["Legacy Compatibility"]) # No prefix to match /setup-complete
router.include_router(workspace_router, prefix="/workspace", tags=["Workspace Management"])
router.include_router(workspace_layers_router, prefix="/workspace", tags=["Workspace Layers"])
router.include_router(web_router, prefix="/web", tags=["Web Capture"])
router.include_router(auth_router, tags=["Authentication & Layers"])
router.include_router(admin_layers_router, tags=["Admin - Layers"])
router.include_router(user_layers_router)
# Audit & Governance
router.include_router(audit_router, prefix="/audit", tags=["Audit & Governance"])

# Distributed Agents
from app.api.v1.agents import router as agents_router
router.include_router(agents_router, prefix="/agents", tags=["Distributed Agents"])

from app.api.v1.meetings import router as meetings_router
router.include_router(meetings_router, prefix="/meetings", tags=["Meeting Intelligence"])

# Evaluation router
from app.api.v1.evaluation import router as evaluation_router
router.include_router(evaluation_router, prefix="/evaluation", tags=["Quality Evaluation"])

# Add plural alias for workspace list (AnythingLLM frontend compatibility)
# Frontend models call /workspaces (plural) while our main router uses /workspace (singular)
@router.get("/workspaces", tags=["Workspace Management"])
async def list_workspaces_alias():
    """Alias for /workspace/ to support AnythingLLM frontend."""
    from app.api.v1.workspace import list_workspaces
    return await list_workspaces()




@router.get("/status")
async def api_status() -> dict:
    """API v1 status endpoint."""
    return {
        "api_version": "v1",
        "status": "operational",
        "endpoints": [
            "/ingest - Document ingestion with chunking preview",
            "/vectors - LanceDB vector operations",
            "/graph - Neo4j GraphRAG operations",
            "/query - Hybrid RAG query routing",
            "/viz - Graph visualization data",
            "/research - Deep research with gpt-researcher",
            "/system - VRAM calculator and utilities",
            "/admin - Protected admin endpoints (requires auth)",
            "/evaluation - RAG Quality fencing",
        ],
    }
