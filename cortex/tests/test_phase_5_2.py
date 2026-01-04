"""
Phase 5-2 Unit Tests

Tests for the Cognitive Core features:
- Memory Service
- Global Search (Community Summaries)
- Prompt Cache
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any


class TestMemoryMiddleware:
    """Tests for memory middleware injection."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = MagicMock()
        request.url.path = "/api/v1/chat"
        request.method = "POST"
        request.state = MagicMock()
        request.state.user = MagicMock()
        request.state.user.id = "test-user-123"
        request.state.memories = []
        return request
    
    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 client."""
        with patch("app.services.memory.middleware.get_mem0_client") as mock:
            client = MagicMock()
            client.search.return_value = [
                {"text": "User prefers dark mode", "score": 0.95},
                {"text": "User is a Python developer", "score": 0.88},
            ]
            mock.return_value = client
            yield client
    
    @pytest.mark.asyncio
    async def test_memory_middleware_injects_context(self, mock_request, mock_mem0_client):
        """Test Case 1: Verify Memory Middleware injects context."""
        from app.services.memory.middleware import memory_middleware
        
        # Mock the body extraction
        mock_request.body = AsyncMock(return_value=b'{"query": "What is my preference?"}')
        
        # Mock call_next
        async def mock_call_next(request):
            return MagicMock()
        
        with patch("app.core.config.settings.ENABLE_MEMORY", True):
            await memory_middleware(mock_request, mock_call_next)
        
        # Verify memories were injected
        assert hasattr(mock_request.state, "memories")
        # The search should have been called with user_id
        mock_mem0_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_memory_middleware_skips_non_chat_endpoints(self, mock_request, mock_mem0_client):
        """Verify middleware skips non-chat endpoints."""
        from app.services.memory.middleware import memory_middleware
        
        mock_request.url.path = "/api/v1/admin/users"
        
        async def mock_call_next(request):
            return MagicMock()
        
        await memory_middleware(mock_request, mock_call_next)
        
        # Search should NOT have been called
        mock_mem0_client.search.assert_not_called()


class TestGlobalSearch:
    """Tests for Global Search via community summaries."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store with community summaries."""
        with patch("app.services.graphrag.query_router.get_vector_store") as mock:
            store = MagicMock()
            store.search.return_value = [
                MagicMock(
                    chunk=MagicMock(
                        id="comm_1",
                        content="This community covers engineering best practices",
                        title="Engineering Practices"
                    ),
                    score=0.92
                )
            ]
            mock.return_value = store
            yield store
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        with patch("app.services.graphrag.query_router.get_embedding_service") as mock:
            service = MagicMock()
            service.embed_text = AsyncMock(return_value=MagicMock(embedding=[0.1] * 1536))
            mock.return_value = service
            yield service
    
    @pytest.mark.asyncio
    async def test_global_search_queries_community_summaries(
        self, mock_vector_store, mock_embedding_service
    ):
        """Test Case 2: Verify Global Search queries community_summaries table."""
        from app.services.graphrag.query_router import HybridQueryRouter
        
        with patch("app.services.graphrag.query_router.get_graph_store"):
            router = HybridQueryRouter()
            
            # Call the community summary search
            results = await router._search_community_summaries(
                query="What are the main themes?",
                layer_ids=["test-layer"],
                top_k=5
            )
            
            # Verify vector store was called with correct table
            mock_vector_store.search.assert_called_once()
            call_kwargs = mock_vector_store.search.call_args.kwargs
            assert call_kwargs.get("table_name") == "community_summaries"


class TestPromptCache:
    """Tests for prompt caching."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        return redis_mock
    
    def test_cache_computes_correct_key(self, mock_redis):
        """Test cache key computation uses SHA256."""
        import hashlib
        from app.services.cache.prompt_cache import PromptCache
        
        cache = PromptCache()
        cache._redis = mock_redis
        cache._initialized = True
        
        system_prompt = "You are a helpful assistant."
        chunk_ids = ["chunk_3", "chunk_1", "chunk_2"]  # Unsorted
        query = "What is AI?"
        
        key = cache._compute_key(system_prompt, chunk_ids, query)
        
        # Verify key format
        assert key.startswith("prompt_cache:")
        
        # Verify SHA256 is used (64 hex chars)
        hash_part = key.replace("prompt_cache:", "")
        assert len(hash_part) == 64
        
        # Verify sorted chunk_ids
        expected_content = system_prompt + "".join(sorted(chunk_ids)) + query
        expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()
        assert hash_part == expected_hash
    
    def test_cache_sets_with_ttl(self, mock_redis):
        """Test Case 3: Verify Cache sets with correct TTL."""
        from app.services.cache.prompt_cache import PromptCache
        
        with patch("app.core.config.settings.ENABLE_PROMPT_CACHE", True):
            with patch("app.core.config.settings.PROMPT_CACHE_TTL", 3600):
                cache = PromptCache()
                cache._redis = mock_redis
                cache._initialized = True
                
                cache.set(
                    system_prompt="System prompt",
                    chunk_ids=["chunk_1"],
                    query="Test query",
                    response="Cached response"
                )
                
                # Verify setex was called with TTL
                mock_redis.setex.assert_called_once()
                call_args = mock_redis.setex.call_args
                assert call_args[0][1] == 3600  # TTL
                assert call_args[0][2] == "Cached response"
    
    def test_cache_get_returns_hit(self, mock_redis):
        """Test cache returns hit when value exists."""
        from app.services.cache.prompt_cache import PromptCache
        
        mock_redis.get.return_value = b"Cached response from Redis"
        
        cache = PromptCache()
        cache._redis = mock_redis
        cache._initialized = True
        
        result = cache.get(
            system_prompt="System",
            chunk_ids=["c1"],
            query="Query"
        )
        
        assert result == "Cached response from Redis"


class TestEntityResolver:
    """Tests for entity resolution."""
    
    @pytest.fixture
    def mock_graph_store(self):
        """Mock graph store with entities."""
        with patch("app.services.graphrag.entity_resolver.get_graph_store") as mock:
            store = MagicMock()
            store.get_entities_by_layer.return_value = [
                MagicMock(id="e1", name="John Doe", type="PERSON"),
                MagicMock(id="e2", name="J. Doe", type="PERSON"),
                MagicMock(id="e3", name="Project Alpha", type="PROJECT"),
            ]
            mock.return_value = store
            yield store
    
    @pytest.fixture
    def mock_embed_service(self):
        """Mock embedding service."""
        import numpy as np
        
        with patch("app.services.graphrag.entity_resolver.get_embedding_service") as mock:
            service = MagicMock()
            # Return similar embeddings for John Doe and J. Doe
            def embed_side_effect(text):
                if "John" in text or "J. Doe" in text:
                    return np.array([0.9, 0.1, 0.0] + [0.0] * 1533)
                else:
                    return np.array([0.1, 0.9, 0.0] + [0.0] * 1533)
            
            service.embed_sync = embed_side_effect
            mock.return_value = service
            yield service
    
    def test_find_duplicates_detects_similar_entities(
        self, mock_graph_store, mock_embed_service
    ):
        """Test duplicate detection finds similar entities."""
        from app.services.graphrag.entity_resolver import EntityResolver
        
        resolver = EntityResolver(threshold=0.9)
        
        duplicates = resolver.find_duplicates(layer_id="test-layer")
        
        # Should find John Doe and J. Doe as duplicates
        assert len(duplicates) >= 1
        
        # Verify structure
        if duplicates:
            dup = duplicates[0]
            assert hasattr(dup, "source_name")
            assert hasattr(dup, "target_name")
            assert hasattr(dup, "similarity_score")


class TestRerankerFactory:
    """Tests for reranker factory pattern."""
    
    def test_factory_selects_cross_encoder_by_default(self):
        """Verify local CrossEncoder is selected by default."""
        from app.services.search.reranker import RerankerService, CrossEncoderReranker
        
        with patch("app.core.config.settings.ENABLE_RERANKING", True):
            with patch("app.core.config.settings.RERANKER_PROVIDER", "local"):
                # Mock CrossEncoder initialization
                with patch.object(CrossEncoderReranker, "__init__", return_value=None):
                    service = RerankerService()
                    assert isinstance(service.reranker, CrossEncoderReranker)
    
    def test_factory_selects_cohere_when_configured(self):
        """Verify Cohere is selected when configured with API key."""
        from app.services.search.reranker import RerankerService, CohereReranker
        
        with patch("app.core.config.settings.ENABLE_RERANKING", True):
            with patch("app.core.config.settings.RERANKER_PROVIDER", "cohere"):
                with patch("app.core.config.settings.COHERE_API_KEY", "test-key"):
                    # Mock Cohere initialization
                    with patch.object(CohereReranker, "__init__", return_value=None):
                        service = RerankerService()
                        assert isinstance(service.reranker, CohereReranker)
