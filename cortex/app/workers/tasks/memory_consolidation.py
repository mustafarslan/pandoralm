"""
Memory Consolidation Task

Celery task for asynchronous memory extraction and storage.
Runs after chat responses to extract facts without blocking the response.
"""
import logging
from typing import Dict, List, Any

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


@celery_app.task(bind=True)
def scheduled_memory_summarization(self, user_id: str, days: int = 1):
    """
    Periodic task to summarize user memories.
    Can be scheduled via Celery Beat or triggered manually.
    """
    import asyncio
    from app.services.memory.consolidation_service import get_consolidation_service
    
    logger.info(f"Starting memory summarization for user {user_id}")
    
    try:
        service = get_consolidation_service()
        # Run async service in sync Celery task
        loop = asyncio.get_event_loop()
        summary = loop.run_until_complete(service.summarize_memories_for_user(user_id, days))
        
        if summary:
            logger.info(f"Generated summary for user {user_id}: {len(summary)} chars")
            return {"status": "success", "summary_len": len(summary)}
        else:
            logger.info(f"No summary generated for user {user_id}")
            return {"status": "skipped", "reason": "no_memories"}
            
    except Exception as exc:
        logger.error(f"Summarization task failed for user {user_id}: {exc}")
        # raise self.retry(exc=exc) # Optional retry
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True, name="cron.trigger_memory_maintenance")
def trigger_memory_maintenance(self) -> Dict[str, Any]:
    """
    Daily cron task to trigger memory maintenance for all active users.
    
    Fan-out pattern:
    1. Find users active in the last 30 days.
    2. Trigger summarization for each.
    3. Trigger cleanup for each.
    """
    import asyncio
    from app.services.audit_service import AuditService
    from app.core.database import async_session_maker
    
    logger.info("Starting daily memory maintenance trigger")
    
    async def _get_users():
        async with async_session_maker() as session:
            svc = AuditService(session)
            return await svc.get_active_users(days=30)
            
    try:
        loop = asyncio.get_event_loop()
        active_users = loop.run_until_complete(_get_users())
        
        triggered_count = 0
        for user_id in active_users:
            if not user_id or user_id == "anonymous":
                continue
                
            # Trigger Summarization (Daily)
            scheduled_memory_summarization.delay(user_id=user_id, days=1)
            
            # Trigger Cleanup (Daily check, but logic checks age)
            cleanup_old_memories.delay(user_id=user_id, max_age_days=90)
            
            triggered_count += 1
            
        logger.info(f"Triggered memory maintenance for {triggered_count} users")
        return {"status": "success", "triggered": triggered_count}
        
    except Exception as exc:
        logger.error(f"Memory maintenance trigger failed: {exc}")
        return {"status": "error", "error": str(exc)}
