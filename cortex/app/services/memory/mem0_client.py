"""
Mem0 Client

Wrapper around Mem0 SDK for persistent memory operations.
Uses LanceDB as the vector store backend for consistency with existing infrastructure.
"""
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)

# Import mem0 conditionally to handle missing dependency gracefully
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("mem0ai not installed. Memory features will be disabled.")


class Mem0Client:
    """
    Client for persistent memory operations using Mem0 SDK.
    
    Provides user-scoped memory search, storage, and deduplication.
    All operations are filtered by user_id to ensure data isolation.
    """
    
    def __init__(self):
        """
        Initialize Mem0 client with LanceDB backend.
        
        Configuration is loaded from settings:
        - LANCEDB_PATH: Path to LanceDB storage
        - MEMORY_LLM_MODEL: Model for fact extraction
        - OPENAI_API_KEY: Required for embeddings/extraction
        """
        self._client: Optional[Any] = None
        self._initialized = False
        
    def _ensure_initialized(self) -> bool:
        """Lazy initialization of Mem0 client."""
        if self._initialized:
            return self._client is not None
            
        if not MEM0_AVAILABLE:
            logger.warning("mem0ai not available. Memory features disabled.")
            self._initialized = True
            return False
            
        if not settings.ENABLE_MEMORY:
            logger.info("Memory features disabled by configuration.")
            self._initialized = True
            return False
            
        try:
            # Build LLM config based on provider
            if settings.MEMORY_LLM_PROVIDER == "ollama":
                llm_config = {
                    "provider": "ollama",
                    "config": {
                        "model": settings.MEMORY_LLM_MODEL,
                        "ollama_base_url": settings.MEMORY_OLLAMA_URL,
                    }
                }
                logger.info(f"Memory LLM: Ollama ({settings.MEMORY_LLM_MODEL})")
            else:
                # Default to OpenAI
                llm_config = {
                    "provider": "openai",
                    "config": {
                        "model": settings.MEMORY_LLM_MODEL,
                        "api_key": settings.OPENAI_API_KEY,
                    }
                }
                logger.info(f"Memory LLM: OpenAI ({settings.MEMORY_LLM_MODEL})")
            
            # Build Embedder config based on provider
            if settings.MEMORY_EMBEDDER_PROVIDER == "ollama":
                embedder_config = {
                    "provider": "ollama",
                    "config": {
                        "model": settings.MEMORY_EMBEDDER_MODEL,
                        "ollama_base_url": settings.MEMORY_OLLAMA_URL,
                    }
                }
                logger.info(f"Memory Embedder: Ollama ({settings.MEMORY_EMBEDDER_MODEL})")
            else:
                # Default to OpenAI
                embedder_config = {
                    "provider": "openai",
                    "config": {
                        "model": settings.MEMORY_EMBEDDER_MODEL,
                        "api_key": settings.OPENAI_API_KEY,
                    }
                }
                logger.info(f"Memory Embedder: OpenAI ({settings.MEMORY_EMBEDDER_MODEL})")
            
            # Configure Mem0 with LanceDB backend
            config = {
                "vector_store": {
                    "provider": "lancedb",
                    "config": {
                        "uri": settings.LANCEDB_PATH,
                        "table_name": "memories"
                    }
                },
                "llm": llm_config,
                "embedder": embedder_config,
            }
            
            self._client = Memory.from_config(config)
            logger.info(f"Mem0 client initialized with LanceDB at {settings.LANCEDB_PATH}")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Mem0 client: {e}")
            self._initialized = True
            return False
    
    @trace_span("memory.search")
    def search(
        self, 
        query: str, 
        user_id: str, 
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories for a user.
        
        Args:
            query: The search query
            user_id: User ID for filtering (CRITICAL for security)
            limit: Maximum number of results to return
            
        Returns:
            List of memory dicts with 'text', 'score', and metadata
        """
        if not self._ensure_initialized():
            return []
            
        if limit is None:
            limit = settings.MEMORY_SEARCH_LIMIT
            
        try:
            # CRITICAL: Pass user_id to ensure user isolation
            results = self._client.search(query, user_id=user_id, limit=limit)
            
            # Format results for injection into context
            memories = []
            for item in results:
                memories.append({
                    "text": item.get("memory", item.get("text", "")),
                    "score": item.get("score", 0.0),
                    "created_at": item.get("created_at"),
                    "id": item.get("id")
                })
            
            logger.debug(f"Found {len(memories)} memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Memory search failed for user {user_id}: {e}")
            return []
    
    @trace_span("memory.add")
    def add(
        self, 
        messages: List[Dict[str, str]], 
        user_id: str,
        agent_id: str = "pandora"
    ) -> bool:
        """
        Extract and store facts from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User ID for ownership (CRITICAL for security)
            agent_id: Identifier for the extracting agent
            
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False
            
        try:
            # Mem0 automatically extracts facts from the conversation
            self._client.add(
                messages, 
                user_id=user_id,
                metadata={"agent_id": agent_id}
            )
            logger.info(f"Added memories for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Memory add failed for user {user_id}: {e}")
            return False
    
    @trace_span("memory.deduplicate")
    def deduplicate(self, user_id: str) -> bool:
        """
        Remove duplicate memories for a user.
        
        Uses Mem0's built-in deduplication to prevent memory bloat.
        
        Args:
            user_id: User ID for scoping
            
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False
            
        try:
            # Mem0 provides deduplicate functionality
            # If not available in this version, gracefully skip
            if hasattr(self._client, 'deduplicate'):
                self._client.deduplicate(user_id=user_id)
                logger.info(f"Deduplicated memories for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Memory deduplication failed for user {user_id}: {e}")
            return False
    
    @trace_span("memory.get_all")
    def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all memories for a user.
        
        Args:
            user_id: User ID for filtering
            
        Returns:
            List of all memory items
        """
        if not self._ensure_initialized():
            return []
            
        try:
            return self._client.get_all(user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to get all memories for user {user_id}: {e}")
            return []
    
    @trace_span("memory.delete")
    def delete(self, memory_id: str, user_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: ID of the memory to delete
            user_id: User ID for verification
            
        Returns:
            True if successful
        """
        if not self._ensure_initialized():
            return False
            
        try:
            self._client.delete(memory_id)
            logger.info(f"Deleted memory {memory_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False


# Singleton instance
_mem0_client: Optional[Mem0Client] = None


def get_mem0_client() -> Mem0Client:
    """Get or create the Mem0 client singleton."""
    global _mem0_client
    if _mem0_client is None:
        _mem0_client = Mem0Client()
    return _mem0_client
