"""
Search Pipeline Orchestrator.
Routes queries to appropriate engines (Vector, Graph, Code) and fuses results.
"""
import logging
from typing import List, Dict, Any, Optional

from app.core.telemetry import trace_span
from app.services.vector_store import get_vector_store
from app.services.graphrag.neo4j_store import get_neo4j_store
from app.services.search.reranker import get_reranker_service
from app.services.router import IntentType
from app.services.graphrag.entity_extractor import get_entity_extractor

logger = logging.getLogger(__name__)

class SearchPipeline:
    """
    Orchestrates the search flow:
    1. Intent -> Route
    2. Parallel Retrieval (Vector / Graph / Code)
    3. Fusion (RRF)
    4. Reranking (Cross-Encoder)
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.graph_store = get_neo4j_store()
        self.reranker = get_reranker_service()

    @trace_span("search.pipeline.run")
    async def run(
        self,
        query: str,
        intent: IntentType,
        workspace_id: str,
        allowed_layers: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:

        results = []

        # 1. Routing & Retrieval
        if intent == IntentType.CODE_GENERATION or self._is_code_query(query):
            # CODE PATH
            results = await self._code_search(query, workspace_id, allowed_layers, limit)
        elif intent == IntentType.THEMATIC:
            # GRAPH PATH (Global)
            results = await self._balanced_search(query, workspace_id, allowed_layers, limit, graph_weight=0.7)
        else:
            # FACTUAL / DEFAULT PATH
            results = await self._balanced_search(query, workspace_id, allowed_layers, limit, graph_weight=0.3)

        # 2. Reranking
        final_results = self.reranker.rerank(query, results, top_k=limit)

        return final_results

    def _is_code_query(self, query: str) -> bool:
        """Heuristic check for code intent if Router missed it."""
        keywords = ["function", "class", "method", "def ", "import ", "const ", "bug in"]
        return any(k in query.lower() for k in keywords)

    async def _code_search(self, query: str, workspace_id: str, allowed_layers: List[str], limit: int):
        """
        Specialized code search:
        1. Vector Search on Code Chunks
        2. Graph Expansion: If Method found, fetch Class context
        """
        # A. Vector Retrieval (LanceDB)
        # Note: In real world, we'd use a sparse index (BM25) for code identifiers.
        # Here we rely on dense embeddings + metadata filtering.
        kb_results = self.vector_store.search(
            query,
            workspace_id=workspace_id,
            allowed_layers=allowed_layers,
            limit=limit * 2
        )

        # B. Context Expansion (Graph)
        expanded_results = []
        for res in kb_results:
            chunk = res.chunk
            item = chunk.to_dict()
            item["score"] = res.score

            # If it's a function/method, try to find parent context
            if getattr(chunk, "node_type", "") in ["function", "method"] and getattr(chunk, "parent_id", None):
                parent_context = self.graph_store.get_entity_context(chunk.parent_id, workspace_id)
                if parent_context:
                    item["context"] = parent_context

            expanded_results.append(item)

        return expanded_results

    async def _balanced_search(self, query: str, workspace_id: str, allowed_layers: List[str], limit: int, graph_weight: float):
        """
        Standard Hybrid Search (Vector + GraphRAG).
        
        Executes in parallel:
        1. Vector Search (Dense Retrieval)
        2. Graph Search (Entity Extraction -> Local Search)
        
        Returns:
            RRF Fused results.
        """
        import asyncio
        
        # Define tasks for parallel execution
        
        async def run_vector_search():
            try:
                vec_res = self.vector_store.search(
                    query,
                    workspace_id=workspace_id,
                    allowed_layers=allowed_layers,
                    limit=limit * 2  # Fetch more for fusion
                )
                return [r.chunk.to_dict() for r in vec_res]
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                return []

        async def run_graph_search():
            try:
                # A. Extract Entities (LLM)
                # Use a very fast model or cache for this to stay real-time
                extractor = get_entity_extractor()
                entities = await extractor.extract_entities(query, chunk_id="query", model=None)
                
                if not entities:
                    return []
                
                entity_names = [e.name for e in entities]
                
                # B. Local Graph Search
                # Finds context from 2-hop neighborhood of extracted entities
                graph_data = self.graph_store.local_search(
                    query_entities=entity_names,
                    workspace_id=workspace_id,
                    allowed_layers=allowed_layers,
                    hops=2,
                    limit=limit * 2
                )
                
                # Convert Entities/Relationships to flat result format
                # For RRF, we need standard result dicts.
                # We prioritize Entities found.
                graph_results = []
                for entity in graph_data.get("entities", []):
                    # Convert to dict if strictly typed
                    item = entity.model_dump() if hasattr(entity, "model_dump") else entity.to_dict() 
                    # Normalize ID for fusion matches (assuming vector store uses same Chunk IDs??)
                    # Note: Vector Store returns CHUNKS, Graph returns ENTITIES.
                    # Fusion is tricky if IDs don't match.
                    # Strategy: Return Graph Entities as distinct results to provide "Concepts".
                    item["source"] = "graph"
                    graph_results.append(item)
                    
                return graph_results
            except Exception as e:
                logger.error(f"Graph search failed: {e}")
                return []

        # Execute Parallel
        try:
            vector_results, graph_results = await asyncio.gather(
                run_vector_search(),
                run_graph_search()
            )
        except Exception as e:
            logger.error(f"Parallel search execution error: {e}")
            # Fallback to serial or just vector if critical failure
            vector_results = []
            graph_results = []

        # 3. Fuse (RRF)
        # Note: We fuse mixed types (Chunks vs Entities). 
        # The UI/Renderer must handle "Entity" type results.
        fused = self.reranker.rrf_fuse(vector_results, graph_results, k=60)
        
        return fused

# Singleton
_pipeline = None

def get_search_pipeline() -> SearchPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = SearchPipeline()
    return _pipeline
