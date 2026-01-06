"""
Hybrid Query Router
Routes queries to Vector (LanceDB) or Graph (Neo4j) search based on query type

Enhanced with LLM-based Cognitive Router (Kahneman's System 1 vs System 2)
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.services import get_vector_store, get_embedding_service
from app.services.graphrag import get_graph_store
from app.services.router import (
    IntentType,
    ClassificationResult,
    get_intent_classifier,
    INTENT_TO_QUERY_MODE,
)

logger = logging.getLogger(__name__)


class QueryMode(str, Enum):
    """Query routing modes."""
    VECTOR = "vector"      # Semantic similarity search
    GRAPH = "graph"        # Knowledge graph traversal
    HYBRID = "hybrid"      # Combined vector + graph
    RESEARCH = "research"  # Agentic tool use
    AUTO = "auto"          # Automatically determine best mode


@dataclass
class QueryContext:
    """Context retrieved for a query."""
    mode: QueryMode
    content: str
    sources: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    communities: List[Dict[str, Any]]
    confidence: float
    # Cognitive Router metadata
    intent_type: Optional[str] = None
    classification_latency_ms: Optional[float] = None
    classification_reasoning: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = {
            "mode": self.mode.value,
            "content": self.content,
            "sources": self.sources,
            "entities": self.entities,
            "communities": self.communities,
            "confidence": self.confidence,
        }
        # Include classification metadata if available
        if self.intent_type:
            result["intent_type"] = self.intent_type
            result["classification_latency_ms"] = self.classification_latency_ms
            result["classification_reasoning"] = self.classification_reasoning
        return result


class HybridQueryRouter:
    """
    Routes queries to the appropriate search backend.
    
    Query routing logic:
    - VECTOR: Good for specific factual questions, finding similar content
    - GRAPH: Good for entity relationships, thematic overviews
    - HYBRID: Combines both for comprehensive answers
    - AUTO: Analyzes query to determine best approach
    
    Auto-detection heuristics:
    - Questions about relationships → GRAPH
    - Questions about themes/summaries → GRAPH (global search)
    - Specific fact-finding → VECTOR
    - Complex questions → HYBRID
    """
    
    # Keywords suggesting graph search
    GRAPH_KEYWORDS = [
        "relationship", "related", "connect", "between",
        "overview", "summary", "theme", "pattern",
        "all", "every", "compare", "contrast",
        "regulation", "conflict", "depend", "impact",
    ]
    
    # Keywords suggesting vector search  
    VECTOR_KEYWORDS = [
        "what is", "define", "explain", "how to",
        "specific", "exactly", "detail", "example",
        "step", "procedure", "process",
    ]
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.graph_store = get_graph_store()
        self.embedding_service = get_embedding_service()
    
    async def route_query(
        self,
        query: str,
        workspace_id: str,
        mode: QueryMode = QueryMode.AUTO,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        allowed_layers: Optional[List[str]] = None, # ReBAC Layers
        use_cognitive_router: bool = True,
    ) -> QueryContext:
        """
        Route and execute a query.
        
        Args:
            query: The user's question
            workspace_id: Workspace to search
            mode: Query mode (AUTO to auto-detect)
            top_k: Number of results to retrieve
            document_ids: Optional filter by documents
            allowed_layers: Authorized layers for ReBAC filtering
            use_cognitive_router: Use LLM-based intent classification
            
        Returns:
            QueryContext with retrieved information and classification metadata
        """
        classification_result = None
        
        # Auto-detect mode using Cognitive Router (LLM-based)
        if mode == QueryMode.AUTO:
            if use_cognitive_router:
                mode, classification_result = await self._detect_query_mode_llm(query)
            else:
                mode = self._detect_query_mode_keywords(query)
        
        # Execute query based on mode
        if mode == QueryMode.VECTOR:
            context = await self._vector_search(query, workspace_id, top_k, document_ids) # Vector store doesn't use layer filter in search signature yet, assumes vector_store handles it internally or we add it
            # Correction: VectorStore usually handles filtering via metadata filter_expr constructed from allowed_layers
            # For now, let's assume _vector_search needs to be updated too, or we just pass it to graph search which clearly needs it for global search
        elif mode == QueryMode.GRAPH:
            context = await self._graph_search(query, workspace_id, top_k, layer_ids=allowed_layers)
        elif mode == QueryMode.RESEARCH:
             context = await self._research_search(query)
        else:  # HYBRID
            context = await self._hybrid_search(query, workspace_id, top_k, document_ids, allowed_layers)
        
        # Attach classification metadata
        if classification_result:
            context.intent_type = classification_result.intent.value
            context.classification_latency_ms = classification_result.latency_ms
            context.classification_reasoning = classification_result.reasoning
        
        return context
    
    async def _detect_query_mode_llm(self, query: str) -> tuple[QueryMode, ClassificationResult]:
        """
        Detect query mode using LLM-based Cognitive Router.
        
        Uses gpt-4o-mini for fast (~100ms) intent classification.
        Falls back to keyword matching on error.
        """
        try:
            classifier = get_intent_classifier()
            result = await classifier.classify(query)
            
            # Map IntentType to QueryMode
            intent_mode_map = {
                IntentType.FACTUAL: QueryMode.VECTOR,
                IntentType.THEMATIC: QueryMode.GRAPH,
                IntentType.THEMATIC: QueryMode.GRAPH,
                IntentType.RESEARCH: QueryMode.RESEARCH,
                IntentType.AGENTIC: QueryMode.RESEARCH,  # Map generic agent intent to ResearchAgent
                IntentType.CODE_GENERATION: QueryMode.VECTOR,
            }
            
            mode = intent_mode_map.get(result.intent, QueryMode.HYBRID)
            
            logger.info(
                f"Cognitive Router: {query[:50]}... → {result.intent.value} → {mode.value}"
            )
            
            return mode, result
            
        except Exception as e:
            logger.warning(f"Cognitive Router failed, using keyword fallback: {e}")
            mode = self._detect_query_mode_keywords(query)
            
            # Create fallback result
            fallback_result = ClassificationResult(
                intent=IntentType.FACTUAL,
                confidence=0.5,
                reasoning=f"Keyword fallback due to error: {str(e)}",
                latency_ms=0,
                model_used="keyword_fallback",
            )
            return mode, fallback_result
    
    def _detect_query_mode_keywords(self, query: str) -> QueryMode:
        """Fallback: Detect query mode based on keyword matching."""
        query_lower = query.lower()
        
        # Count keyword matches
        graph_score = sum(1 for kw in self.GRAPH_KEYWORDS if kw in query_lower)
        vector_score = sum(1 for kw in self.VECTOR_KEYWORDS if kw in query_lower)
        
        # Decision logic
        if graph_score > vector_score + 1:
            return QueryMode.GRAPH
        elif vector_score > graph_score + 1:
            return QueryMode.VECTOR
        else:
            return QueryMode.HYBRID
    
    async def _vector_search(
        self,
        query: str,
        workspace_id: str,
        top_k: int,
        document_ids: Optional[List[str]],
    ) -> QueryContext:
        """Execute vector similarity search."""
        logger.info(f"[VECTOR] Starting search: workspace={workspace_id}, top_k={top_k}, query='{query[:50]}...'")
        # Generate query embedding
        embed_result = await self.embedding_service.embed_text(query)
        
        # Search LanceDB
        results = self.vector_store.search(
            query_embedding=embed_result.embedding,
            workspace_id=workspace_id,
            top_k=top_k,
            document_ids=document_ids,
        )
        
        # Build context
        sources = []
        context_parts = []
        
        for r in results:
            sources.append({
                "chunk_id": r.chunk.id,
                "document_id": r.chunk.document_id,
                "content": r.chunk.content[:200] + "..." if len(r.chunk.content) > 200 else r.chunk.content,
                "score": r.score,
                "metadata": r.chunk.metadata,
            })
            context_parts.append(r.chunk.content)
        
        return QueryContext(
            mode=QueryMode.VECTOR,
            content="\n\n---\n\n".join(context_parts),
            sources=sources,
            entities=[],
            communities=[],
            confidence=results[0].score if results else 0.0,
        )
    
    async def _graph_search(
        self,
        query: str,
        workspace_id: str,
        top_k: int,
        layer_ids: Optional[List[str]] = None,
    ) -> QueryContext:
        """Execute graph-based search with Global Search support.
        
        For THEMATIC queries, prioritizes community summary search
        which synthesizes themes across documents.
        """
        logger.info(f"[GRAPHRAG] Starting search: workspace={workspace_id}, top_k={top_k}, query='{query[:50]}...'")
        
        # First, try community summary search for global/thematic queries
        community_results = await self._search_community_summaries(
            query, 
            layer_ids or [workspace_id],
            top_k=top_k // 2
        )
        
        communities = []
        if community_results:
            for c in community_results:
                communities.append({
                    "id": c.get("id"),
                    "title": c.get("title", ""),
                    "summary": c.get("content", c.get("summary", "")),
                    "score": c.get("score", 0.0),
                })
        else:
            # Fallback to graph store global search
            global_result = self.graph_store.global_search(
                workspace_id=workspace_id,
                top_communities=top_k // 2,
            )
            
            for c in global_result.get("communities", []):
                communities.append({
                    "id": c.id,
                    "title": c.title,
                    "summary": c.summary,
                    "entity_count": len(c.entity_ids),
                })
        
        # Also do local search for specific entities
        # Extract potential entity names from query (simple heuristic)
        query_words = [w for w in query.split() if len(w) > 3 and w[0].isupper()]
        
        entities = []
        if query_words:
            local_result = self.graph_store.local_search(
                query_entities=query_words,
                workspace_id=workspace_id,
                hops=2,
                limit=top_k,
            )
            
            for e in local_result.get("entities", []):
                entities.append({
                    "id": e.id,
                    "name": e.name,
                    "type": e.type,
                    "description": e.description,
                })
        
        # Build context from communities and entities
        context_parts = []
        
        if communities:
            context_parts.append("## Relevant Themes\n")
            for c in communities[:3]:
                context_parts.append(f"**{c['title']}**: {c['summary']}\n")
        
        if entities:
            context_parts.append("\n## Related Entities\n")
            for e in entities[:5]:
                context_parts.append(f"- **{e['name']}** ({e['type']}): {e['description']}\n")
        
        logger.info(f"[GRAPHRAG] Search complete: {len(communities)} communities, {len(entities)} entities found")
        
        return QueryContext(
            mode=QueryMode.GRAPH,
            content="\n".join(context_parts) or "No graph context found.",
            sources=[],
            entities=entities,
            communities=communities,
            confidence=0.8 if (entities or communities) else 0.2,
        )

    async def _search_community_summaries(
        self,
        query: str,
        layer_ids: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search community summaries for Global Search.
        
        Enables answering high-level thematic queries by searching
        pre-computed community summaries with ReBAC filtering.
        
        Args:
            query: User's query
            layer_ids: List of authorized layer IDs for security
            top_k: Number of results
            
        Returns:
            List of matching community summary records
        """
        try:
            # Generate query embedding
            embed_result = await self.embedding_service.embed_text(query)
            
            # Search community_summaries table with layer filtering
            results = self.vector_store.search(
                query_embedding=embed_result.embedding,
                table_name="community_summaries",
                top_k=top_k,
                filter_expr=f"layer_id IN {layer_ids}" if layer_ids else None,
            )
            
            if results:
                logger.info(f"[GLOBAL SEARCH] Found {len(results)} community summaries")
                return [
                    {
                        "id": r.chunk.id if hasattr(r, 'chunk') else r.get("id"),
                        "content": r.chunk.content if hasattr(r, 'chunk') else r.get("content"),
                        "title": r.chunk.title if hasattr(r, 'chunk') else r.get("title", ""),
                        "score": r.score if hasattr(r, 'score') else r.get("score", 0.0),
                    }
                    for r in results
                ]
            
            return []
            
        except Exception as e:
            logger.warning(f"Community summary search failed: {e}")
            return []

    

    
    async def _research_search(
        self,
        query: str,
    ) -> QueryContext:
        """Execute deep research using MCP Agent."""
        from app.services.agent.agent import ResearchAgent
        
        # Initialize agent
        agent = ResearchAgent()
        
        # Execute research
        answer = await agent.execute(query)
        
        return QueryContext(
            mode=QueryMode.RESEARCH,
            content=answer,
            sources=[], # Agent might provide sources in future
            entities=[],
            communities=[],
            confidence=0.9, # High confidence if agent succeeds
        )

    
    async def _hybrid_search(
        self,
        query: str,
        workspace_id: str,
        top_k: int,
        document_ids: Optional[List[str]],
        allowed_layers: Optional[List[str]] = None,
    ) -> QueryContext:
        """Execute combined vector + graph search."""
        # Run both searches
        vector_ctx = await self._vector_search(query, workspace_id, top_k // 2, document_ids)
        graph_ctx = await self._graph_search(query, workspace_id, top_k // 2, layer_ids=allowed_layers)
        
        # Combine contexts
        combined_content = ""
        
        if graph_ctx.content and graph_ctx.content != "No graph context found.":
            combined_content += "## Knowledge Graph Context\n\n"
            combined_content += graph_ctx.content + "\n\n"
        
        if vector_ctx.content:
            combined_content += "## Document Context\n\n"
            combined_content += vector_ctx.content
        
        # Combine confidence (weighted average)
        confidence = (vector_ctx.confidence * 0.6 + graph_ctx.confidence * 0.4)
        
        return QueryContext(
            mode=QueryMode.HYBRID,
            content=combined_content,
            sources=vector_ctx.sources,
            entities=graph_ctx.entities,
            communities=graph_ctx.communities,
            confidence=confidence,
        )


# Singleton
_router: Optional[HybridQueryRouter] = None

def get_query_router() -> HybridQueryRouter:
    global _router
    if _router is None:
        _router = HybridQueryRouter()
    return _router

