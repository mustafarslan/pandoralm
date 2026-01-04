"""
Cron Tasks for PandoraLM
Scheduled background jobs running via Celery Beat

Tasks:
- regenerate_stale_communities: Nightly (3 AM UTC) regeneration of community summaries
"""
import asyncio
import logging
from typing import Dict, Any, List

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# =============================================================================
# Nightly Community Summarizer (3 AM UTC)
# =============================================================================

@celery_app.task(
    bind=True,
    name="cron.regenerate_stale_communities",
    soft_time_limit=3600,   # 1 hour soft limit
    time_limit=7200,        # 2 hour hard limit
)
def regenerate_stale_communities(
    self,
    workspace_id: str = None,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    Nightly cron job - regenerates summaries for stale communities.
    
    Why: Community detection (Leiden) affects global structure. Doing it
    per-file during incremental indexing is wasteful. Doing it nightly
    is efficient and ensures community summaries stay fresh.
    
    Logic:
    1. Pop all stale IDs from Redis: spop("stale_communities", batch_size)
    2. For each ID:
       - Fetch all entities in that community
       - Re-run the Summarization LLM prompt
       - Update the Community node in Neo4j
    3. If any fail, re-add them to the stale set for next run
    
    Args:
        workspace_id: Optional - specific workspace to process.
                     If None, processes all workspaces.
        batch_size: Max communities to process per run (default: 100)
    
    Returns:
        Dict with processing results
    """
    from app.services.graphrag.stale_community_tracker import get_stale_community_tracker
    from app.services.graphrag.neo4j_store import get_graph_store
    from app.services.graphrag.community_detector import get_community_detector
    
    stale_tracker = get_stale_community_tracker()
    graph_store = get_graph_store()
    detector = get_community_detector()
    
    results = {
        "workspaces_processed": 0,
        "communities_regenerated": 0,
        "communities_failed": 0,
        "errors": [],
    }
    
    # Determine workspaces to process
    if workspace_id:
        workspaces = [workspace_id]
    else:
        # For now, get workspaces from Neo4j by querying unique workspace_ids
        # In production, this should come from a workspace service
        workspaces = _get_active_workspaces(graph_store)
    
    logger.info(
        f"[Cron] Starting community summarization for {len(workspaces)} workspace(s)"
    )
    
    for ws_id in workspaces:
        # Pop stale communities (atomic, thread-safe)
        stale_ids = stale_tracker.pop_stale(ws_id, batch_size)
        
        if not stale_ids:
            logger.info(f"[Cron] No stale communities in workspace '{ws_id}'")
            continue
        
        logger.info(
            f"[Cron] Processing {len(stale_ids)} stale communities in workspace '{ws_id}'"
        )
        
        results["workspaces_processed"] += 1
        failed_ids = []
        
        for community_id in stale_ids:
            try:
                # Fetch community from Neo4j
                community = graph_store.get_community_by_id(community_id, ws_id)
                
                if not community:
                    logger.warning(
                        f"[Cron] Community '{community_id}' not found in workspace '{ws_id}'"
                    )
                    continue
                
                # Fetch entities for this community
                entity_ids = community.entity_ids
                entities = []
                for eid in entity_ids:
                    entity = graph_store.get_entity(eid, ws_id)
                    if entity:
                        entities.append(entity)
                
                if not entities:
                    logger.warning(
                        f"[Cron] No entities found for community '{community_id}'"
                    )
                    continue
                
                # Generate new summary using LLM
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    new_summary, new_title = loop.run_until_complete(
                        detector.generate_community_summary(entities)
                    )
                finally:
                    loop.close()
                
                # Update community in Neo4j
                updated = graph_store.update_community_summary(
                    community_id=community_id,
                    workspace_id=ws_id,
                    new_summary=new_summary,
                    new_title=new_title,
                )
                
                if updated:
                    results["communities_regenerated"] += 1
                    logger.debug(
                        f"[Cron] Regenerated summary for community '{community_id}'"
                    )
                else:
                    failed_ids.append(community_id)
                    results["communities_failed"] += 1
                    
            except Exception as e:
                logger.error(
                    f"[Cron] Failed to regenerate community '{community_id}': {e}"
                )
                failed_ids.append(community_id)
                results["communities_failed"] += 1
                results["errors"].append(f"{community_id}: {str(e)}")
        
        # Re-add failed communities for retry on next run
        if failed_ids:
            stale_tracker.re_add_failed(failed_ids, ws_id)
            logger.warning(
                f"[Cron] Re-added {len(failed_ids)} failed communities for retry"
            )
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={
            'workspace': ws_id,
            'regenerated': results["communities_regenerated"],
            'failed': results["communities_failed"],
        })
    
    logger.info(
        f"[Cron] Community summarization complete: "
        f"{results['communities_regenerated']} regenerated, "
        f"{results['communities_failed']} failed"
    )
    
    return results


def _get_active_workspaces(graph_store) -> List[str]:
    """
    Get list of workspace IDs that have graph data.
    
    Helper function to find workspaces to process when no specific
    workspace is provided.
    """
    try:
        with graph_store.driver.session() as session:
            result = session.run(
                "MATCH (c:Community) RETURN DISTINCT c.workspace_id AS ws"
            )
            return [record["ws"] for record in result if record["ws"]]
    except Exception as e:
        logger.error(f"[Cron] Failed to get workspaces: {e}")
        return []


# =============================================================================
# Manual Trigger Endpoint Support
# =============================================================================

@celery_app.task(
    bind=True,
    name="cron.trigger_community_regeneration",
)
def trigger_community_regeneration(
    self,
    workspace_id: str,
    community_ids: List[str] = None,
) -> Dict[str, Any]:
    """
    Manually trigger community regeneration for specific communities.
    
    Used by Admin Console for on-demand summary regeneration.
    
    Args:
        workspace_id: Workspace containing the communities
        community_ids: Optional list of specific community IDs.
                      If None, regenerates all stale communities.
    
    Returns:
        Dict with processing results
    """
    from app.services.graphrag.stale_community_tracker import get_stale_community_tracker
    
    if community_ids:
        # Mark specific communities as stale, then run the summarizer
        stale_tracker = get_stale_community_tracker()
        stale_tracker.mark_stale(community_ids, workspace_id)
        logger.info(
            f"[Cron] Marked {len(community_ids)} communities for regeneration"
        )
    
    # Run the summarizer for this workspace
    return regenerate_stale_communities(
        workspace_id=workspace_id,
        batch_size=len(community_ids) if community_ids else 100,
    )


# =============================================================================
# Chat Message Retention Policy (Daily at 4 AM UTC)
# =============================================================================

@celery_app.task(
    bind=True,
    name="cron.purge_old_chat_messages",
    soft_time_limit=600,   # 10 min soft limit
    time_limit=1200,       # 20 min hard limit
)
def purge_old_chat_messages(self) -> Dict[str, Any]:
    """
    Enterprise retention policy - purges chat messages older than CHAT_RETENTION_DAYS.
    
    Why: Enterprise compliance (GDPR, HIPAA) and storage management require
    automatic data lifecycle management. Messages older than the retention
    period are permanently deleted.
    
    Configuration:
        CHAT_RETENTION_DAYS: Number of days to keep messages (default: 30)
        Set to 0 to disable automatic purging.
    
    Returns:
        Dict with purge results
    """
    import os
    import httpx
    from datetime import datetime, timedelta
    
    retention_days = int(os.getenv("CHAT_RETENTION_DAYS", "30"))
    
    if retention_days <= 0:
        logger.info("[Cron] Chat retention disabled (CHAT_RETENTION_DAYS <= 0)")
        return {"status": "disabled", "messages_deleted": 0}
    
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    logger.info(
        f"[Cron] Purging chat messages older than {retention_days} days "
        f"(before {cutoff_date.isoformat()})"
    )
    
    results = {
        "retention_days": retention_days,
        "cutoff_date": cutoff_date.isoformat(),
        "messages_deleted": 0,
        "errors": [],
    }
    
    try:
        # Call Core API to purge messages
        # This keeps the database logic in Core (Prisma) rather than duplicating
        core_url = os.getenv("CORE_API_URL", "http://pandora-core:3001")
        
        response = httpx.post(
            f"{core_url}/api/system/purge-old-chats",
            json={"cutoff_date": cutoff_date.isoformat()},
            timeout=300.0,
            headers={"Authorization": f"Bearer {os.getenv('SYSTEM_API_KEY', '')}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results["messages_deleted"] = data.get("deleted_count", 0)
            logger.info(f"[Cron] Purged {results['messages_deleted']} old chat messages")
        else:
            error_msg = f"Core API returned {response.status_code}"
            results["errors"].append(error_msg)
            logger.error(f"[Cron] {error_msg}")
            
    except Exception as e:
        error_msg = f"Failed to purge chats: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(f"[Cron] {error_msg}")
    
    return results
