"""
Graph Operations Celery Tasks (Admin Console)
Async tasks for graph manipulation using APOC

Includes:
- Entity merging with apoc.refactor.mergeNodes
- Community summary regeneration
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# Job status tracking (shared with vector_ops)
_job_status: Dict[str, Dict[str, Any]] = {}


def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status."""
    _job_status[job_id] = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        **kwargs,
    }


# =============================================================================
# Entity Merge Task (APOC)
# =============================================================================

@celery_app.task(
    bind=True,
    name="graph_ops.merge_entities",
    queue="heavy_lifting",
    max_retries=2,
)
def merge_entities_task(
    self,
    target_id: str,
    source_ids: List[str],
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Merge multiple entities into one using APOC.
    
    Uses apoc.refactor.mergeNodes to physically merge nodes,
    combining properties and transferring relationships.
    """
    from app.services.graphrag import get_graph_store
    
    job_id = self.request.id
    update_job_status(job_id, "running", progress=0.0)
    
    logger.info(f"[GraphOps] Merging {len(source_ids)} entities into {target_id} (job: {job_id})")
    
    graph_store = get_graph_store()
    
    try:
        # Verify all entities exist
        update_job_status(job_id, "running", progress=0.2, phase="validating")
        
        target_entity = graph_store.get_entity(target_id, workspace_id)
        if not target_entity:
            raise ValueError(f"Target entity not found: {target_id}")
        
        for source_id in source_ids:
            source_entity = graph_store.get_entity(source_id, workspace_id)
            if not source_entity:
                raise ValueError(f"Source entity not found: {source_id}")
        
        # Execute APOC merge for each source
        update_job_status(job_id, "running", progress=0.4, phase="merging")
        
        merged_count = 0
        for i, source_id in enumerate(source_ids):
            try:
                # Use APOC merge
                result = _execute_apoc_merge(graph_store, target_id, source_id, workspace_id)
                if result:
                    merged_count += 1
                    logger.info(f"[GraphOps] Merged {source_id} into {target_id}")
            except Exception as e:
                logger.error(f"[GraphOps] Failed to merge {source_id}: {e}")
            
            progress = 0.4 + (0.5 * (i + 1) / len(source_ids))
            update_job_status(job_id, "running", progress=progress, phase="merging")
        
        # Finalize
        update_job_status(job_id, "completed", progress=1.0, result={
            "target_id": target_id,
            "merged_count": merged_count,
            "total_sources": len(source_ids),
        })
        
        return {
            "status": "completed",
            "job_id": job_id,
            "target_id": target_id,
            "merged_count": merged_count,
            "workspace_id": workspace_id,
        }
        
    except Exception as e:
        logger.error(f"[GraphOps] Merge failed: {e}")
        update_job_status(job_id, "failed", error=str(e))
        raise


def _execute_apoc_merge(graph_store, target_id: str, source_id: str, workspace_id: str) -> bool:
    """
    Execute APOC node merge in Neo4j.
    
    Requires APOC plugin enabled in Neo4j.
    """
    # Build the Cypher query using APOC
    query = """
    MATCH (target:Entity {id: $target_id, workspace_id: $workspace_id})
    MATCH (source:Entity {id: $source_id, workspace_id: $workspace_id})
    CALL apoc.refactor.mergeNodes([target, source], {
        properties: 'combine',
        mergeRels: true
    })
    YIELD node
    RETURN node.id AS merged_id, node.name AS merged_name
    """
    
    try:
        with graph_store.driver.session() as session:
            result = session.run(
                query,
                target_id=target_id,
                source_id=source_id,
                workspace_id=workspace_id,
            )
            record = result.single()
            return record is not None
    except Exception as e:
        # If APOC not available, fallback to manual merge
        logger.warning(f"APOC merge failed, attempting manual merge: {e}")
        return _manual_merge(graph_store, target_id, source_id, workspace_id)


def _manual_merge(graph_store, target_id: str, source_id: str, workspace_id: str) -> bool:
    """
    Fallback manual merge when APOC is not available.
    
    1. Copy relationships from source to target
    2. Delete source node
    """
    try:
        with graph_store.driver.session() as session:
            # Transfer outgoing relationships
            session.run("""
                MATCH (source:Entity {id: $source_id, workspace_id: $workspace_id})-[r]->(other)
                MATCH (target:Entity {id: $target_id, workspace_id: $workspace_id})
                MERGE (target)-[newRel:RELATED_TO]->(other)
                SET newRel = properties(r)
                DELETE r
            """, source_id=source_id, target_id=target_id, workspace_id=workspace_id)
            
            # Transfer incoming relationships
            session.run("""
                MATCH (other)-[r]->(source:Entity {id: $source_id, workspace_id: $workspace_id})
                MATCH (target:Entity {id: $target_id, workspace_id: $workspace_id})
                MERGE (other)-[newRel:RELATED_TO]->(target)
                SET newRel = properties(r)
                DELETE r
            """, source_id=source_id, target_id=target_id, workspace_id=workspace_id)
            
            # Combine source_documents
            session.run("""
                MATCH (source:Entity {id: $source_id, workspace_id: $workspace_id})
                MATCH (target:Entity {id: $target_id, workspace_id: $workspace_id})
                SET target.source_documents = target.source_documents + source.source_documents
                SET target.description = CASE 
                    WHEN source.description IS NOT NULL AND target.description IS NOT NULL 
                    THEN target.description + '; ' + source.description 
                    ELSE COALESCE(target.description, source.description)
                END
            """, source_id=source_id, target_id=target_id, workspace_id=workspace_id)
            
            # Delete source node
            session.run("""
                MATCH (source:Entity {id: $source_id, workspace_id: $workspace_id})
                DELETE source
            """, source_id=source_id, workspace_id=workspace_id)
            
            return True
    except Exception as e:
        logger.error(f"Manual merge failed: {e}")
        return False


# =============================================================================
# Community Summary Regeneration Task
# =============================================================================

@celery_app.task(
    bind=True,
    name="graph_ops.regenerate_summary",
    queue="heavy_lifting",
)
def regenerate_summary_task(
    self,
    community_id: str,
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Regenerate AI summary for a community.
    
    Fetches community entities and uses LLM to generate new summary.
    """
    from app.services.graphrag import get_graph_store, get_community_detector
    
    job_id = self.request.id
    update_job_status(job_id, "running", progress=0.0)
    
    logger.info(f"[GraphOps] Regenerating summary for community {community_id} (job: {job_id})")
    
    graph_store = get_graph_store()
    detector = get_community_detector()
    
    try:
        # Get community
        communities = graph_store.get_communities(workspace_id=workspace_id)
        community = next((c for c in communities if c.id == community_id), None)
        
        if not community:
            raise ValueError(f"Community not found: {community_id}")
        
        update_job_status(job_id, "running", progress=0.3, phase="fetching_entities")
        
        # Get entities in community
        entities = []
        for entity_id in community.entity_ids:
            entity = graph_store.get_entity(entity_id, workspace_id)
            if entity:
                entities.append(entity)
        
        update_job_status(job_id, "running", progress=0.5, phase="generating_summary")
        
        # Generate new summary using LLM
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            new_summary = loop.run_until_complete(
                detector.summarize_community(entities)
            )
        finally:
            loop.close()
        
        # Update community in Neo4j
        update_job_status(job_id, "running", progress=0.8, phase="updating")
        
        community.summary = new_summary
        graph_store.upsert_community(community, workspace_id)
        
        update_job_status(job_id, "completed", progress=1.0, result={
            "community_id": community_id,
            "new_summary": new_summary[:200] + "..." if len(new_summary) > 200 else new_summary,
        })
        
        return {
            "status": "completed",
            "job_id": job_id,
            "community_id": community_id,
            "summary_preview": new_summary[:200],
        }
        
    except Exception as e:
        logger.error(f"[GraphOps] Summary regeneration failed: {e}")
        update_job_status(job_id, "failed", error=str(e))
        raise
