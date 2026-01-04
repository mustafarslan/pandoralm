"""
Prompt Cache Service

Redis-based cache for pre-computed context to reduce LLM latency.
Uses SHA256 hash of context components for cache keys.
"""
import hashlib
import logging
from typing import Optional

from app.core.config import settings
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)


class PromptCache:
    """
    Redis-based cache for prompt contexts.
    
    Reduces Time-To-First-Token (TTFT) by caching pre-computed context
    for repetitive queries or long conversations with static context.
    
    Key Strategy: SHA256(system_prompt + sorted(chunk_ids) + query)
    This ensures cache invalidation if retrieved documents change.
    """
    
    def __init__(self):
        """Initialize prompt cache with Redis connection."""
        self._redis = None
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """Lazy initialization of Redis connection."""
        if self._initialized:
            return self._redis is not None
        
        if not settings.ENABLE_PROMPT_CACHE:
            logger.info("Prompt cache disabled by configuration")
            self._initialized = True
            return False
        
        try:
            import redis
            self._redis = redis.from_url(settings.REDIS_URL)
            # Test connection
            self._redis.ping()
            logger.info("Prompt cache connected to Redis")
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for prompt cache: {e}")
            self._initialized = True
            return False
    
    def _compute_key(
        self, 
        system_prompt: str, 
        chunk_ids: list, 
        query: str
    ) -> str:
        """
        Compute cache key using SHA256.
        
        Key components:
        - system_prompt: The fixed system instructions
        - chunk_ids: Sorted list of retrieved chunk IDs
        - query: The user's query
        
        Returns:
            SHA256 hash string prefixed with 'prompt_cache:'
        """
        content = system_prompt + "".join(sorted(chunk_ids)) + query
        hash_digest = hashlib.sha256(content.encode()).hexdigest()
        return f"prompt_cache:{hash_digest}"
    
    @trace_span("prompt_cache.get")
    def get(
        self,
        system_prompt: str,
        chunk_ids: list,
        query: str,
    ) -> Optional[str]:
        """
        Get cached response for the given context.
        
        Args:
            system_prompt: System prompt used
            chunk_ids: List of chunk IDs in context
            query: User query
            
        Returns:
            Cached response string or None if not found
        """
        if not self._ensure_initialized():
            return None
        
        try:
            key = self._compute_key(system_prompt, chunk_ids, query)
            value = self._redis.get(key)
            
            if value:
                logger.debug(f"Cache HIT for query: {query[:50]}...")
                return value.decode() if isinstance(value, bytes) else value
            
            logger.debug(f"Cache MISS for query: {query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Cache get failed: {e}")
            return None
    
    @trace_span("prompt_cache.set")
    def set(
        self,
        system_prompt: str,
        chunk_ids: list,
        query: str,
        response: str,
    ) -> bool:
        """
        Cache a response for the given context.
        
        Args:
            system_prompt: System prompt used
            chunk_ids: List of chunk IDs in context
            query: User query
            response: LLM response to cache
            
        Returns:
            True if cached successfully
        """
        if not self._ensure_initialized():
            return False
        
        try:
            key = self._compute_key(system_prompt, chunk_ids, query)
            self._redis.setex(
                key,
                settings.PROMPT_CACHE_TTL,
                response
            )
            logger.debug(f"Cached response for query: {query[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False
    
    @trace_span("prompt_cache.invalidate")
    def invalidate_pattern(self, pattern: str = "*") -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Redis key pattern to match (default: all)
            
        Returns:
            Number of keys deleted
        """
        if not self._ensure_initialized():
            return 0
        
        try:
            full_pattern = f"prompt_cache:{pattern}"
            keys = self._redis.keys(full_pattern)
            
            if keys:
                deleted = self._redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self._ensure_initialized():
            return {"enabled": False}
        
        try:
            info = self._redis.info("stats")
            keys = self._redis.keys("prompt_cache:*")
            
            return {
                "enabled": True,
                "ttl_seconds": settings.PROMPT_CACHE_TTL,
                "cached_entries": len(keys),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception:
            return {"enabled": True, "error": "Failed to get stats"}


# Singleton
_prompt_cache: Optional[PromptCache] = None


def get_prompt_cache() -> PromptCache:
    """Get or create the prompt cache singleton."""
    global _prompt_cache
    if _prompt_cache is None:
        _prompt_cache = PromptCache()
    return _prompt_cache
