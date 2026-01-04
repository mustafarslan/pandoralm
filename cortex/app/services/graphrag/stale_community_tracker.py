"""
Stale Community Tracker
Redis-based atomic tracker for communities needing re-summarization.

Uses Redis SET operations for thread-safe, idempotent tracking:
- SADD: Mark community as stale (idempotent, atomic)
- SPOP: Atomically pop N stale communities for processing
- SREM: Remove specific community from stale set
- SCARD: Get count of stale communities

Why Redis SET?
1. Atomic: Multiple workers can safely mark communities without race conditions
2. Idempotent: Adding the same community twice has no effect
3. Efficient: O(1) for add/remove, O(N) for pop
"""
import redis
import logging
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class StaleCommunityTracker:
    """
    Thread-safe Redis tracker for communities needing re-summarization.
    
    After incremental graph indexing, affected communities are marked "stale".
    The nightly cron job pops stale communities and regenerates summaries.
    
    Key Format: pandora:stale_communities:{workspace_id}
    """
    
    KEY_PREFIX = "pandora:stale_communities"
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize tracker with Redis connection.
        
        Args:
            redis_client: Optional pre-configured Redis client.
                         If not provided, creates one from settings.REDIS_URL.
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,  # We'll decode manually for type safety
            )
    
    def _key(self, workspace_id: str) -> str:
        """Get Redis key for workspace's stale communities."""
        return f"{self.KEY_PREFIX}:{workspace_id}"
    
    def mark_stale(self, community_ids: List[str], workspace_id: str) -> int:
        """
        Atomically mark communities as stale (needing re-summarization).
        
        This operation is idempotent - marking the same community twice
        has no effect on the set.
        
        Args:
            community_ids: List of community IDs to mark as stale
            workspace_id: Workspace the communities belong to
            
        Returns:
            Number of communities newly added (not already in set)
        """
        if not community_ids:
            return 0
            
        key = self._key(workspace_id)
        added = self.redis.sadd(key, *community_ids)
        
        logger.info(
            f"Marked {added} communities as stale in workspace '{workspace_id}' "
            f"(total marked: {len(community_ids)})"
        )
        
        return added
    
    def pop_stale(self, workspace_id: str, count: int = 100) -> List[str]:
        """
        Atomically pop up to `count` stale communities for processing.
        
        This removes the communities from the set, ensuring no other worker
        will process them. If processing fails, they should be re-added.
        
        Args:
            workspace_id: Workspace to pop communities from
            count: Maximum number of communities to pop
            
        Returns:
            List of community IDs to process
        """
        key = self._key(workspace_id)
        popped = self.redis.spop(key, count)
        
        if not popped:
            return []
        
        # Decode bytes to strings
        community_ids = [
            c.decode('utf-8') if isinstance(c, bytes) else c 
            for c in popped
        ]
        
        logger.info(
            f"Popped {len(community_ids)} stale communities from workspace '{workspace_id}'"
        )
        
        return community_ids
    
    def get_stale_count(self, workspace_id: str) -> int:
        """
        Get count of stale communities (for monitoring/dashboards).
        
        Args:
            workspace_id: Workspace to check
            
        Returns:
            Number of communities waiting for re-summarization
        """
        key = self._key(workspace_id)
        return self.redis.scard(key)
    
    def mark_fresh(self, community_id: str, workspace_id: str) -> bool:
        """
        Remove a specific community from the stale set.
        
        Use this after successfully regenerating a community's summary.
        
        Args:
            community_id: Community to mark as fresh
            workspace_id: Workspace the community belongs to
            
        Returns:
            True if community was in the set and removed, False otherwise
        """
        key = self._key(workspace_id)
        removed = self.redis.srem(key, community_id)
        return removed > 0
    
    def re_add_failed(self, community_ids: List[str], workspace_id: str) -> int:
        """
        Re-add communities that failed to process.
        
        If the nightly job fails to summarize a community, it should be
        re-added to the stale set for retry on the next run.
        
        Args:
            community_ids: Communities that failed processing
            workspace_id: Workspace the communities belong to
            
        Returns:
            Number of communities added back
        """
        if not community_ids:
            return 0
            
        key = self._key(workspace_id)
        added = self.redis.sadd(key, *community_ids)
        
        logger.warning(
            f"Re-added {added} failed communities to stale set in workspace '{workspace_id}'"
        )
        
        return added
    
    def get_all_stale(self, workspace_id: str) -> List[str]:
        """
        Get all stale community IDs without removing them.
        
        Use for debugging/monitoring only. For processing, use pop_stale().
        
        Args:
            workspace_id: Workspace to check
            
        Returns:
            List of all stale community IDs
        """
        key = self._key(workspace_id)
        members = self.redis.smembers(key)
        
        if not members:
            return []
            
        return [
            m.decode('utf-8') if isinstance(m, bytes) else m 
            for m in members
        ]


# Singleton instance
_tracker: Optional[StaleCommunityTracker] = None


def get_stale_community_tracker() -> StaleCommunityTracker:
    """Get or create singleton StaleCommunityTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = StaleCommunityTracker()
    return _tracker
