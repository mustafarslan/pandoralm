"""
Documents API Endpoints
Status polling and document management for async ingestion pipeline.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.document_status import DocumentStatusResponse, ProcessingStatus
from app.services.document_status_service import get_document_status_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list")
async def list_documents(
    workspace_id: str = Query(..., description="Workspace ID to list documents for"),
):
    """
    List all documents for a workspace.

    Used by Admin Console to populate document dropdowns.
    """
    from app.services import get_vector_store

    vector_store = get_vector_store()

    # Get unique document IDs from chunks
    chunks = vector_store.get_chunks(workspace_id=workspace_id, limit=10000)

    # Group by document_id to get unique documents
    doc_map = {}
    for chunk in chunks:
        doc_id = chunk.document_id
        if doc_id not in doc_map:
            doc_map[doc_id] = {
                "id": doc_id,
                "name": chunk.metadata.get("source_title", doc_id) if chunk.metadata else doc_id,
                "chunk_count": 0,
            }
        doc_map[doc_id]["chunk_count"] += 1

    documents = list(doc_map.values())

    return {
        "workspace_id": workspace_id,
        "documents": documents,
        "total": len(documents),
    }


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str) -> DocumentStatusResponse:
    """
    Poll document processing status.

    Returns the current status of both vector and graph indexing,
    enabling the "eventual consistency" UX pattern.

    - If vector_status=completed: Document is queryable via vector search
    - If graph_status=completed: Deep analysis (GraphRAG) is available
    """
    service = get_document_status_service()
    status = service.get(document_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Document status not found: {document_id}"
        )

    # Build user-friendly message
    if status.vector_status == ProcessingStatus.COMPLETED and status.graph_status == ProcessingStatus.COMPLETED:
        message = "Fully indexed. Vector and graph search available."
    elif status.vector_status == ProcessingStatus.COMPLETED:
        if status.graph_status == ProcessingStatus.PROCESSING:
            message = f"Vector search available. Deep analysis processing ({int(status.graph_progress * 100)}%)..."
        elif status.graph_status == ProcessingStatus.FAILED:
            message = f"Vector search available. Graph indexing failed: {status.error_message or 'Unknown error'}"
        else:
            message = "Vector search available. Deep analysis pending..."
    elif status.vector_status == ProcessingStatus.PROCESSING:
        message = f"Processing for search ({int(status.vector_progress * 100)}%)..."
    elif status.vector_status == ProcessingStatus.FAILED:
        message = f"Processing failed: {status.error_message or 'Unknown error'}"
    else:
        message = "Queued for processing..."

    return DocumentStatusResponse(
        document_id=status.document_id,
        workspace_id=status.workspace_id,
        vector_status=status.vector_status,
        graph_status=status.graph_status,
        vector_progress=status.vector_progress,
        graph_progress=status.graph_progress,
        is_vector_ready=status.is_vector_ready(),
        is_graph_ready=status.is_graph_ready(),
        message=message,
        chunk_count=status.chunk_count,
        entity_count=status.entity_count,
    )


@router.get("/workspace/{workspace_id}")
async def list_workspace_documents(
    workspace_id: str,
    include_completed: bool = Query(True, description="Include completed documents"),
    include_processing: bool = Query(True, description="Include processing documents"),
):
    """
    List all documents for a workspace with their processing status.
    """
    service = get_document_status_service()
    documents = service.get_by_workspace(workspace_id)

    # Filter based on query params
    results = []
    for doc in documents:
        if not include_completed and doc.is_fully_indexed():
            continue
        if not include_processing and doc.vector_status == ProcessingStatus.PROCESSING:
            continue
        results.append(doc.to_dict())

    return {
        "workspace_id": workspace_id,
        "total": len(results),
        "documents": results,
    }


@router.delete("/{document_id}")
async def delete_document_status(document_id: str):
    """
    Delete document status record.

    Note: This only removes the status tracking, not the actual
    document data from LanceDB or Neo4j.
    """
    service = get_document_status_service()
    deleted = service.delete(document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Document status not found: {document_id}"
        )

    return {"status": "deleted", "document_id": document_id}
