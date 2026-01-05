"""
Document Ingestion API
Async ingestion with immediate 202 response and background processing.

Two-tier processing:
1. Fast Lane: Vectorization (seconds) → queryable immediately
2. Heavy Lifting: GraphRAG (minutes) → deep analysis available later
"""
import os
import uuid
import logging
from typing import Optional


from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.models.document_status import IngestJobResponse, ProcessingStatus
from app.services.document_status_service import get_document_status_service
from app.workers.tasks.indexing import vectorize_document
from app.auth.keycloak import verifier
from app.core.security import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


class IngestRequest(BaseModel):
    """Request for document ingestion."""
    filename: str = Field(..., description="Filename in the hotdir")
    workspace_id: str = Field(default="default", description="Workspace ID")
    target_layer_id: str = Field(..., description="Target Knowledge Layer ID (Required)")
    trigger_graph_indexing: bool = Field(
        default=True,
        description="Whether to trigger GraphRAG indexing after vectorization"
    )


class SyncIngestRequest(BaseModel):
    """Request for synchronous document ingestion (legacy)."""
    filename: str


@router.post("/process", status_code=202, response_model=IngestJobResponse)
async def process_document_async(
    file: UploadFile = File(...),
    workspace_id: str = Form("default"),
    target_layer_id: str = Form(...),
    trigger_graph_indexing: bool = Form(True),
    token_payload: dict = Depends(verifier.verify_token) # Extract User ID for JIT check
) -> IngestJobResponse:

    """
    Process a document asynchronously (returns 202 Accepted).
    
    This endpoint:
    1. Receives a file upload (multipart/form-data)
    2. Saves it to the hotdir
    3. Creates a DocumentStatus record
    4. Queues vectorization task (Fast Lane)
    5. Returns immediately with job_id
    
    The vectorization worker will:
    - Extract text, chunk, embed, store in LanceDB
    - Mark status as VECTOR_READY (queryable via vector search)
    - Chain to GraphRAG indexing (if enabled)
    
    Use GET /api/v1/document/{document_id}/status to poll progress.
    """
    hotdir = "/app/hotdir"  # Mounted via Docker
    
    # Ensure hotdir exists
    if not os.path.exists(hotdir):
        os.makedirs(hotdir, exist_ok=True)
        
    # Sanitize filename
    filename = os.path.basename(file.filename)
    fullpath = os.path.join(hotdir, filename)
    
    # Save file
    try:
        with open(fullpath, "wb") as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                f.write(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Generate document ID
    document_id = str(uuid.uuid4())
    
    # Create status record
    status_service = get_document_status_service()
    status_service.create(
        document_id=document_id,
        workspace_id=workspace_id,
        filename=filename,
    )
    
    logger.info(f"Queuing document for processing: {document_id} ({filename})")
    
    # Get User ID from token
    user_id = token_payload.get("sub") or token_payload.get("preferred_username")

    # Queue vectorization task (Fast Lane) with JIT context
    task = vectorize_document.delay(
        document_id=document_id,
        workspace_id=workspace_id,
        layer_id=target_layer_id,
        user_id=user_id,
        filename=filename,
        file_path=fullpath,
        trigger_graph_indexing=trigger_graph_indexing,
    )
    
    # Update status with task ID
    status_service.update(document_id, vector_task_id=task.id)
    
    return IngestJobResponse(
        status="accepted",
        job_id=task.id,
        document_id=document_id,
        workspace_id=workspace_id,
        message=f"Document '{filename}' queued for processing. Vector search will be available shortly.",
    )


@router.post("/process/sync", dependencies=[Depends(require_auth)])
async def process_document_sync(request: SyncIngestRequest):
    """
    Process a document synchronously (legacy endpoint).
    
    This mimics the vector-admin document-processor API.
    Use /process (POST) for the recommended async flow.
    """
    from app.services.document_processor.extract_text import extract_text
    
    hotdir = "/app/hotdir"  # Mounted via Docker
    
    # Validation
    fullpath = os.path.normpath(os.path.join(hotdir, request.filename))
    if not fullpath.startswith(hotdir):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not os.path.exists(fullpath):
        raise HTTPException(status_code=404, detail=f"File not found: {request.filename}")

    logger.info(f"Processing (sync): {request.filename}")
    
    try:
        success, reason, metadata = extract_text(hotdir, request.filename)
        if not success:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {reason}")
        
        return {
            "success": True,
            "filename": request.filename,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

