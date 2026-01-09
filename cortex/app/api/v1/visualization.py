"""
Graph Visualization Endpoints
Data export for knowledge graph visualization
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.core.security import require_auth
from app.services.graphrag import get_graph_store

router = APIRouter()


class VisNode(BaseModel):
    """Node for visualization."""
    id: str
    label: str
    type: str
    description: str
    size: int = 10


class VisEdge(BaseModel):
    """Edge for visualization."""
    id: str
    source: str
    target: str
    label: str
    weight: float = 1.0


class GraphDataResponse(BaseModel):
    """Graph data for visualization libraries like Cytoscape, D3, etc."""
    nodes: List[VisNode]
    edges: List[VisEdge]
    stats: dict


@router.get("/{workspace_id}", response_model=GraphDataResponse, dependencies=[Depends(require_auth)])
async def get_graph_visualization_data(
    workspace_id: str,
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to filter"),
    limit_nodes: int = Query(100, le=500),
    limit_edges: int = Query(200, le=1000),
) -> GraphDataResponse:
    """
    Get graph data formatted for visualization.

    Returns nodes and edges in a format compatible with:
    - Cytoscape.js
    - D3.js Force Graph
    - vis.js Network
    """
    target_ws = "*" if workspace_id.lower() == "global" else workspace_id
    graph_store = get_graph_store()

    # Check connectivity
    if not graph_store.verify_connectivity():
        raise HTTPException(status_code=503, detail="Neo4j database unavailable")

    # Parse entity types filter
    type_filter = None
    if entity_types:
        type_filter = [t.strip() for t in entity_types.split(",")]

    # Get entities
    if type_filter:
        entities = []
        for t in type_filter:
            entities.extend(graph_store.get_entities(
                workspace_id=target_ws,
                entity_type=t,
                limit=limit_nodes // len(type_filter),
            ))
    else:
        entities = graph_store.get_entities(
            workspace_id=workspace_id,
            limit=limit_nodes,
        )

    # Get relationships between these entities
    entity_ids = {e.id for e in entities}
    all_relationships = graph_store.get_relationships(
        workspace_id=workspace_id,
        limit=limit_edges,
    )

    # Filter relationships to only those between our entities
    relationships = [
        r for r in all_relationships
        if r.source_id in entity_ids and r.target_id in entity_ids
    ]

    # Build visualization data
    nodes = []
    type_counts = {}

    for entity in entities:
        # Size based on number of connections
        connection_count = sum(
            1 for r in relationships
            if r.source_id == entity.id or r.target_id == entity.id
        )

        nodes.append(VisNode(
            id=entity.id,
            label=entity.name,
            type=entity.type,
            description=entity.description[:100] if entity.description else "",
            size=max(10, min(50, connection_count * 5)),
        ))

        type_counts[entity.type] = type_counts.get(entity.type, 0) + 1

    edges = [
        VisEdge(
            id=r.id,
            source=r.source_id,
            target=r.target_id,
            label=r.type,
            weight=r.weight,
        )
        for r in relationships
    ]

    return GraphDataResponse(
        nodes=nodes,
        edges=edges,
        stats={
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": type_counts,
            "workspace_id": workspace_id,
        },
    )


@router.get("/{workspace_id}/cytoscape", dependencies=[Depends(require_auth)])
async def get_cytoscape_format(
    workspace_id: str,
    limit: int = Query(100, le=300),
) -> dict:
    """
    Get graph data in Cytoscape.js format.

    Returns elements array ready for Cytoscape initialization.
    """
    graph_store = get_graph_store()

    entities = graph_store.get_entities(workspace_id=workspace_id, limit=limit)
    entity_ids = {e.id for e in entities}

    relationships = graph_store.get_relationships(workspace_id=workspace_id, limit=limit * 2)
    relationships = [r for r in relationships if r.source_id in entity_ids and r.target_id in entity_ids]

    # Build Cytoscape elements
    elements = []

    # Add nodes
    for entity in entities:
        elements.append({
            "data": {
                "id": entity.id,
                "label": entity.name,
                "type": entity.type,
                "description": entity.description,
            },
            "classes": entity.type.lower(),
        })

    # Add edges
    for rel in relationships:
        elements.append({
            "data": {
                "id": rel.id,
                "source": rel.source_id,
                "target": rel.target_id,
                "label": rel.type,
                "weight": rel.weight,
            },
        })

    return {
        "elements": elements,
        "style": get_default_cytoscape_style(),
    }


def get_default_cytoscape_style() -> List[dict]:
    """Get default Cytoscape style configuration."""
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "background-color": "#6366f1",
                "color": "#fff",
                "text-valign": "center",
                "text-halign": "center",
                "font-size": "10px",
                "width": "40px",
                "height": "40px",
            },
        },
        {
            "selector": "node.person",
            "style": {"background-color": "#f59e0b"},
        },
        {
            "selector": "node.organization",
            "style": {"background-color": "#10b981"},
        },
        {
            "selector": "node.concept",
            "style": {"background-color": "#8b5cf6"},
        },
        {
            "selector": "node.regulation",
            "style": {"background-color": "#ef4444"},
        },
        {
            "selector": "node.technology",
            "style": {"background-color": "#3b82f6"},
        },
        {
            "selector": "edge",
            "style": {
                "width": 2,
                "line-color": "#94a3b8",
                "target-arrow-color": "#94a3b8",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "label": "data(label)",
                "font-size": "8px",
                "text-rotation": "autorotate",
            },
        },
    ]


@router.get("/{workspace_id}/communities", dependencies=[Depends(require_auth)])
async def get_community_visualization(
    workspace_id: str,
    level: int = Query(0, ge=0, le=5),
) -> dict:
    """
    Get community structure for visualization.

    Returns hierarchical community data for treemap or sunburst charts.
    """
    graph_store = get_graph_store()

    communities = graph_store.get_communities(workspace_id=workspace_id, level=level)

    # Build hierarchical structure
    community_data = []
    for comm in communities:
        community_data.append({
            "id": comm.id,
            "name": comm.title,
            "summary": comm.summary,
            "value": len(comm.entity_ids),
            "level": comm.level,
            "entities": comm.entity_ids[:10],  # Limit for response size
        })

    return {
        "communities": community_data,
        "total": len(community_data),
        "level": level,
        "workspace_id": workspace_id,
    }
