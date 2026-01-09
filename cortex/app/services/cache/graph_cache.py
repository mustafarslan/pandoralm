"""
Graph Query Cache Service

Redis-based cache for expensive graph traversals (Local/Global Search).
"""
import hashlib
import json
import logging
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)


class GraphQueryCache:
    """
    Redis-based cache for graph query results.

    Caches the output of local_search and global_search to improve latency
    for repeated queries on the same graph state.
    """

    def __init__(self):
        self._redis = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return self._redis is not None

        if not settings.ENABLE_PROMPT_CACHE: # Reusing same enable flag for now
            self._initialized = True
            return False

        try:
            import redis
            self._redis = redis.from_url(settings.REDIS_URL)
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for graph cache: {e}")
            self._initialized = True
            return False

    def _compute_key(self, workspace_id: str, query_type: str, params: Dict[str, Any]) -> str:
        """
        Compute cache key.
        Key = graph_cache:{workspace_id}:{query_type}:{hash(params)}
        """
        # Sort params for consistency
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()

        return f"graph_cache:{workspace_id}:{query_type}:{param_hash}"

    @trace_span("graph_cache.get")
    def get(self, workspace_id: str, query_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._ensure_initialized():
            return None

        try:
            key = self._compute_key(workspace_id, query_type, params)
            value = self._redis.get(key)

            if value:
                # Deserialize from JSON
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Graph cache get failed: {e}")
            return None

    @trace_span("graph_cache.set")
    def set(self, workspace_id: str, query_type: str, params: Dict[str, Any], result: Dict[str, Any], ttl: int = 3600) -> bool:
        if not self._ensure_initialized():
            return False

        try:
            key = self._compute_key(workspace_id, query_type, params)
            # Serialize to JSON (assuming result allows it - Entity dataclasses need conversion first)
            # neo4j_store returns dicts/lists of objects. We need to handle object serialization if passed raw objects.
            # But the caller (neo4j_store) generates 'Entities' which are dataclasses.
            # So the result passed here MUST be JSON serializable.
            # We will handle serialization in the caller or assume dicts.

            self._redis.setex(key, ttl, json.dumps(result))
            return True
        except Exception as e:
            logger.error(f"Graph cache set failed: {e}")
            return False

    def invalidate(self, workspace_id: str):
        """Invalidate all cache for a workspace (e.g. after indexing)."""
        if not self._ensure_initialized():
            return

        try:
            pattern = f"graph_cache:{workspace_id}:*"
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} graph cache entries for {workspace_id}")
        except Exception as e:
            logger.error(f"Graph cache invalidation failed: {e}")

# Singleton
_graph_cache = None

def get_graph_cache():
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = GraphQueryCache()
    return _graph_cache
