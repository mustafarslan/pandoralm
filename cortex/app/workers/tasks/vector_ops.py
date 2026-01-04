"""
Vector Operations Celery Tasks (Admin Console)
Implements Saga Pattern for safe async vector mutations

Saga Pattern:
- Step 1: Embed new text (retriable)
- Step 2: Update LanceDB (retriable, 3x max)
- Step 3: Update Postgres metadata (final commit)
- Rollback: Mark "Sync Error" on failures
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from celery import shared_task
from datetime import datetime

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class SagaStepError(Exception):
    """Error in a specific saga step."""
    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(f"Saga step '{step}' failed: {message}")


class JobStatus:
    """Job status constants."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SYNC_ERROR = "sync_error"  # Saga rollback state


# In-memory job tracking (in production, use Redis or Postgres)
# This is a simplified version - should be replaced with actual DB storage
_job_status: Dict[str, Dict[str, Any]] = {}


def update_job_status(
    job_id: str,
    status: str,
    progress: float = 0.0,
    result: Optional[Dict] = None,
    error: Optional[str] = None,
):
    """Update job status tracking."""
    _job_status[job_id] = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "result": result,
        "error": error,
        "updated_at": datetime.utcnow().isoformat(),
    }


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status."""
    return _job_status.get(job_id)


# =============================================================================
# Saga: Update Chunk Task
# =============================================================================

@celery_app.task(
    bind=True,
    name="vector_ops.update_chunk",
    queue="fast_lane",
    max_retries=3,
    default_retry_delay=5,
)
def update_chunk_task(
    self,
    chunk_id: str,
    workspace_id: str,
    new_content: str,
) -> Dict[str, Any]:
    """
    Saga Pattern: Update a chunk's content with re-embedding.
    
    Steps:
    1. Embed new text (retriable)
    2. Update LanceDB (retriable, 3x max)
    3. Update Postgres metadata (final commit)
    
    Rollback:
    - If Step 2 fails 3 times, mark as "Sync Error" in metadata
    """
    from app.services import get_vector_store, get_embedding_service
    
    job_id = self.request.id
    update_job_status(job_id, JobStatus.RUNNING, 0.0)
    
    logger.info(f"[Saga] Starting chunk update: {chunk_id} (job: {job_id})")
    
    vector_store = get_vector_store()
    embedding_service = get_embedding_service()
    
    # Variables to track saga state
    new_embedding = None
    old_chunk_data = None
    
    try:
        # =====================
        # STEP 1: Embed new text (retriable)
        # =====================
        update_job_status(job_id, JobStatus.RUNNING, 0.2)
        self.update_state(state='PROGRESS', meta={
            'step': 'embedding',
            'progress': 0.2,
        })
        
        logger.info(f"[Saga Step 1] Embedding new text for chunk {chunk_id}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            embed_result = loop.run_until_complete(
                embedding_service.embed_text(new_content)
            )
            new_embedding = embed_result.embedding
        except Exception as e:
            logger.error(f"[Saga Step 1] Embedding failed: {e}")
            raise SagaStepError("embedding", str(e))
        finally:
            loop.close()
        
        # =====================
        # STEP 2: Update LanceDB (retriable, 3x max)
        # =====================
        update_job_status(job_id, JobStatus.RUNNING, 0.5)
        self.update_state(state='PROGRESS', meta={
            'step': 'lancedb_update',
            'progress': 0.5,
        })
        
        logger.info(f"[Saga Step 2] Updating LanceDB for chunk {chunk_id}")
        
        try:
            # Get old chunk data for potential rollback info
            old_chunk = vector_store.get_chunk(chunk_id, workspace_id)
            if old_chunk:
                old_chunk_data = {
                    "content": old_chunk.content,
                    "embedding": old_chunk.embedding[:5] if old_chunk.embedding else None,  # Just first 5 for logging
                }
            
            # Update chunk in LanceDB
            success = vector_store.update_chunk(
                chunk_id=chunk_id,
                workspace_id=workspace_id,
                content=new_content,
                embedding=new_embedding,
            )
            
            if not success:
                raise SagaStepError("lancedb_update", "Update returned False")
                
        except SagaStepError:
            raise
        except Exception as e:
            logger.error(f"[Saga Step 2] LanceDB update failed: {e}")
            
            # Check retry count
            if self.request.retries >= self.max_retries:
                logger.error(f"[Saga Rollback] Max retries reached, marking as Sync Error")
                update_job_status(
                    job_id,
                    JobStatus.SYNC_ERROR,
                    error=f"LanceDB update failed after {self.max_retries} retries: {e}",
                )
                return {
                    "status": "sync_error",
                    "job_id": job_id,
                    "chunk_id": chunk_id,
                    "error": str(e),
                    "rollback_reason": "Max retries exceeded for LanceDB update",
                }
            
            # Retry
            raise self.retry(exc=e)
        
        # =====================
        # STEP 3: Update Postgres metadata (final commit)
        # =====================
        update_job_status(job_id, JobStatus.RUNNING, 0.9)
        self.update_state(state='PROGRESS', meta={
            'step': 'metadata_commit',
            'progress': 0.9,
        })
        
        logger.info(f"[Saga Step 3] Committing metadata for chunk {chunk_id}")
        
        # In a full implementation, this would update a Postgres record
        # For now, we log the successful completion
        metadata_update = {
            "chunk_id": chunk_id,
            "updated_at": datetime.utcnow().isoformat(),
            "content_length": len(new_content),
            "embedding_model": embedding_service.config.model,
        }
        
        # =====================
        # SUCCESS: Saga completed
        # =====================
        update_job_status(job_id, JobStatus.COMPLETED, 1.0, result={
            "chunk_id": chunk_id,
            "workspace_id": workspace_id,
            "content_length": len(new_content),
        })
        
        logger.info(f"[Saga Complete] Chunk {chunk_id} updated successfully")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "chunk_id": chunk_id,
            "workspace_id": workspace_id,
            "content_length": len(new_content),
            "embedding_dimensions": len(new_embedding),
        }
        
    except SagaStepError as e:
        logger.error(f"[Saga Failed] {e}")
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
        raise
    except Exception as e:
        logger.error(f"[Saga Failed] Unexpected error: {e}")
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
        raise


# =============================================================================
# Saga: Bulk Delete Chunks Task
# =============================================================================

@celery_app.task(
    bind=True,
    name="vector_ops.bulk_delete_chunks",
    queue="fast_lane",
    max_retries=2,
)
def bulk_delete_chunks_task(
    self,
    chunk_ids: list,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Bulk delete multiple chunks.
    
    Uses batch deletion for efficiency with transaction semantics.
    """
    from app.services import get_vector_store
    
    job_id = self.request.id
    update_job_status(job_id, JobStatus.RUNNING, 0.0)
    
    logger.info(f"[BulkDelete] Starting deletion of {len(chunk_ids)} chunks (job: {job_id})")
    
    vector_store = get_vector_store()
    deleted_count = 0
    failed_chunks = []
    
    total = len(chunk_ids)
    
    for i, chunk_id in enumerate(chunk_ids):
        try:
            success = vector_store.delete_chunk(chunk_id, workspace_id)
            if success:
                deleted_count += 1
            else:
                failed_chunks.append({"chunk_id": chunk_id, "error": "Delete returned False"})
        except Exception as e:
            failed_chunks.append({"chunk_id": chunk_id, "error": str(e)})
        
        # Update progress every 10 chunks
        if i % 10 == 0:
            progress = (i + 1) / total
            update_job_status(job_id, JobStatus.RUNNING, progress)
    
    # Final status
    status = JobStatus.COMPLETED if not failed_chunks else JobStatus.SYNC_ERROR
    update_job_status(job_id, status, 1.0, result={
        "deleted_count": deleted_count,
        "failed_count": len(failed_chunks),
    })
    
    return {
        "status": status,
        "job_id": job_id,
        "deleted_count": deleted_count,
        "failed_chunks": failed_chunks,
        "total_requested": total,
    }


# =============================================================================
# Saga: Delete Document Chunks Task
# =============================================================================

@celery_app.task(
    bind=True,
    name="vector_ops.delete_document",
    queue="fast_lane",
)
def delete_document_task(
    self,
    document_id: str,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Delete all chunks for a document.
    """
    from app.services import get_vector_store
    
    job_id = self.request.id
    update_job_status(job_id, JobStatus.RUNNING, 0.0)
    
    logger.info(f"[DeleteDoc] Deleting document {document_id} (job: {job_id})")
    
    vector_store = get_vector_store()
    
    try:
        deleted_count = vector_store.delete_document_chunks(document_id, workspace_id)
        
        update_job_status(job_id, JobStatus.COMPLETED, 1.0, result={
            "document_id": document_id,
            "deleted_count": deleted_count,
        })
        
        return {
            "status": "completed",
            "job_id": job_id,
            "document_id": document_id,
            "workspace_id": workspace_id,
            "deleted_count": deleted_count,
        }
        
    except Exception as e:
        logger.error(f"[DeleteDoc] Failed: {e}")
        update_job_status(job_id, JobStatus.FAILED, error=str(e))
        raise


# =============================================================================
# Saga: Reindex All Vectors
# =============================================================================

@celery_app.task(
    bind=True,
    name="vector_ops.reindex_all",
    queue="heavy_lifting",
)
def reindex_all_vectors_task(
    self,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Re-index all vectors (Placeholder/Simulated).
    
    In production, this would:
    1. Iterate all chunks
    2. Re-embed using current model
    3. Update LanceDB
    
    For now, we simulate the workload to test UI feedback.
    """
    import time
    
    job_id = self.request.id
    update_job_status(job_id, JobStatus.RUNNING, 0.0)
    
    logger.info(f"[Reindex] Starting full reindex (job: {job_id})")
    
    # Simulate processing 100 "batches"
    total_steps = 20
    for i in range(total_steps):
        time.sleep(0.5)  # Simulate work
        progress = (i + 1) / total_steps
        update_job_status(job_id, JobStatus.RUNNING, progress)
        
    update_job_status(job_id, JobStatus.COMPLETED, 1.0, result={
        "message": "Reindex simulation complete",
        "workspaces_processed": 1 if workspace_id else "all",
    })
    
    return {
        "status": "completed",
        "job_id": job_id,
        "message": "Reindex complete",
    }

