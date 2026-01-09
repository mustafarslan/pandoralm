import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.services.search.pipeline import SearchPipeline
from app.services.router import IntentType

# Mock Results
MOCK_VECTOR_RESULT = [
    MagicMock(chunk=MagicMock(to_dict=lambda: {"id": "v1", "content": "vector content", "score": 0.9}))
]
MOCK_GRAPH_ENTITIES = [
    MagicMock(name="Entity1", model_dump=lambda: {"id": "e1", "name": "Entity1", "type": "T1"})
]
MOCK_LOCAL_SEARCH_RESULT = {
    "entities": MOCK_GRAPH_ENTITIES,
    "relationships": []
}

@pytest.mark.asyncio
async def test_balanced_search_flow():
    """
    Verify that _balanced_search:
    1. Calls vector store
    2. Calls entity extractor
    3. Calls graph store local_search
    4. Fuses results
    """
    
    # Mock Dependencies
    with patch("app.services.search.pipeline.get_vector_store") as mock_get_vec, \
         patch("app.services.search.pipeline.get_neo4j_store") as mock_get_graph, \
         patch("app.services.search.pipeline.get_reranker_service") as mock_get_rerank, \
         patch("app.services.search.pipeline.get_entity_extractor") as mock_get_extractor:

        # Setup Mocks
        vector_store = MagicMock()
        vector_store.search.return_value = MOCK_VECTOR_RESULT
        mock_get_vec.return_value = vector_store
        
        graph_store = MagicMock()
        graph_store.local_search.return_value = MOCK_LOCAL_SEARCH_RESULT
        mock_get_graph.return_value = graph_store
        
        reranker = MagicMock()
        reranker.rrf_fuse.return_value = [{"id": "fused"}]
        reranker.rerank.return_value = [{"id": "final"}]
        mock_get_rerank.return_value = reranker
        
        extractor = AsyncMock()
        entity_mock = MagicMock()
        entity_mock.name = "Entity1"
        extractor.extract_entities.return_value = [entity_mock]
        mock_get_extractor.return_value = extractor

        # Initialize Pipeline
        pipeline = SearchPipeline()
        
        # Execute
        results = await pipeline.run(
            query="test query",
            intent=IntentType.FACTUAL,
            workspace_id="ws1",
            allowed_layers=["default"]
        )
        
        # Verify Calls
        
        # 1. Vector Search Called
        vector_store.search.assert_called_once()
        
        # 2. Entity Extraction Called
        extractor.extract_entities.assert_called_once_with("test query", chunk_id="query", model=None)
        
        # 3. Graph Local Search Called (since extraction succeeded)
        graph_store.local_search.assert_called_once()
        call_args = graph_store.local_search.call_args[1]
        assert "Entity1" in call_args["query_entities"]
        
        # 4. Fusion Called
        reranker.rrf_fuse.assert_called_once()
