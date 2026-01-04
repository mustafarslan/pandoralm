"""
Memory Consolidation Task

Celery task for asynchronous memory extraction and storage.
Runs after chat responses to extract facts without blocking the response.
"""
import logging
from typing import Dict, List

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    rate_limit="10/m",  # Prevents API token burn during traffic spikes
    max_retries=3,
    default_retry_delay=30,
)
def consolidate_memory(self, user_id: str, messages: List[Dict[str, str]]):
    """
    Extract and store facts from a conversation asynchronously.
    
    This task is triggered after a chat response is sent to the user.
    It decouples the heavy memory extraction from the synchronous chat flow.
    
    Rate limit of 10/m prevents exhausting OpenAI TPM limits during
    concurrent user traffic spikes.
    
    Args:
        user_id: User ID for memory ownership (CRITICAL for security)
        messages: List of message dicts with 'role' and 'content'
    """
    if not settings.ENABLE_MEMORY:
        logger.debug("Memory features disabled, skipping consolidation")
        return {"status": "skipped", "reason": "disabled"}
    
    try:
        # Import here to avoid circular imports
        from app.services.memory.mem0_client import get_mem0_client
        
        client = get_mem0_client()
        
        # Step 1: Extract and add new facts
        logger.info(f"Consolidating memory for user {user_id}, {len(messages)} messages")
        add_success = client.add(messages, user_id=user_id, agent_id="pandora-cortex")
        
        if not add_success:
            logger.warning(f"Memory add failed for user {user_id}")
            return {"status": "partial", "add": False, "dedupe": False}
        
        # Step 2: Deduplicate to prevent bloat
        dedupe_success = client.deduplicate(user_id=user_id)
        
        logger.info(
            f"Memory consolidation complete for user {user_id}: "
            f"add={add_success}, dedupe={dedupe_success}"
        )
        
        return {"status": "success", "add": add_success, "dedupe": dedupe_success}
        
    except Exception as exc:
        logger.error(f"Memory consolidation failed for user {user_id}: {exc}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def cleanup_old_memories(self, user_id: str, max_age_days: int = 90):
    """
    Clean up old memories for a user.
    
    Optional maintenance task to remove stale memories.
    
    Args:
        user_id: User ID for scoping
        max_age_days: Remove memories older than this
    """
    try:
        from app.services.memory.mem0_client import get_mem0_client
        import time
        
        client = get_mem0_client()
        memories = client.get_all(user_id=user_id)
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        deleted_count = 0
        
        for mem in memories:
            created_at = mem.get("created_at", 0)
            if created_at < cutoff_time:
                if client.delete(mem.get("id"), user_id):
                    deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old memories for user {user_id}")
        return {"status": "success", "deleted": deleted_count}
        
    except Exception as exc:
        logger.error(f"Memory cleanup failed for user {user_id}: {exc}")
        return {"status": "error", "error": str(exc)}
