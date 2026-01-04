"""
Reranker Service
Implements advanced reranking using Cross-Encoders and Reciprocal Rank Fusion (RRF).
Supports multiple providers via Factory Pattern: local (CrossEncoder) or Cohere API.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.telemetry import trace_span

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract base class for rerankers."""
    
    @abstractmethod
    def rerank(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank chunks based on query relevance."""
        pass


class CrossEncoderReranker(BaseReranker):
    """Local Cross-Encoder based reranker using sentence-transformers."""
    
    def __init__(self, model_name: str = None):
        self.model = None
        model_name = model_name or settings.RERANKER_MODEL
        
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading CrossEncoder model: {model_name}")
            self.model = CrossEncoder(model_name)
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder model: {e}")
    
    @trace_span("reranker.cross_encoder.rerank")
    def rerank(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank using local Cross-Encoder model."""
        if not self.model or not chunks:
            return chunks[:top_k]
        
        # Prepare pairs for cross-encoder
        pairs = [[query, chunk.get("content", "")] for chunk in chunks]
        
        # Predict scores
        scores = self.model.predict(pairs)
        
        # Attach scores
        for i, chunk in enumerate(chunks):
            chunk["score"] = float(scores[i])
        
        # Sort descending by score
        reranked = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        
        return reranked[:top_k]


class CohereReranker(BaseReranker):
    """Cohere API based reranker for production use."""
    
    def __init__(self, api_key: str = None):
        self.client = None
        api_key = api_key or settings.COHERE_API_KEY
        
        if not api_key:
            logger.warning("Cohere API key not configured, reranking disabled")
            return
        
        try:
            import cohere
            self.client = cohere.Client(api_key)
            logger.info("Cohere reranker initialized")
        except ImportError:
            logger.error("cohere package not installed. Install with: pip install cohere")
        except Exception as e:
            logger.error(f"Failed to initialize Cohere client: {e}")
    
    @trace_span("reranker.cohere.rerank")
    def rerank(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Rerank using Cohere Rerank API."""
        if not self.client or not chunks:
            return chunks[:top_k]
        
        try:
            documents = [chunk.get("content", "") for chunk in chunks]
            
            response = self.client.rerank(
                query=query,
                documents=documents,
                top_n=top_k,
                model="rerank-english-v2.0"
            )
            
            # Reorder chunks based on Cohere results
            reranked = []
            for result in response.results:
                chunk = chunks[result.index].copy()
                chunk["score"] = result.relevance_score
                reranked.append(chunk)
            
            return reranked
            
        except Exception as e:
            logger.error(f"Cohere rerank failed: {e}")
            # Fallback: return original order
            return chunks[:top_k]


class RerankerService:
    """
    Reranks retrieval results to improve precision.
    Uses Factory Pattern to support multiple reranking backends.
    """
    
    def __init__(self):
        """Initialize reranker based on configuration."""
        self.reranker: Optional[BaseReranker] = None
        
        if not settings.ENABLE_RERANKING:
            logger.info("Reranking disabled by configuration")
            return
        
        # Factory Pattern: Select reranker based on provider
        if settings.RERANKER_PROVIDER == "cohere":
            if settings.COHERE_API_KEY:
                self.reranker = CohereReranker()
                logger.info("Using Cohere reranker")
            else:
                logger.warning("Cohere selected but no API key, falling back to local")
                self.reranker = CrossEncoderReranker()
        else:
            self.reranker = CrossEncoderReranker()
            logger.info("Using local CrossEncoder reranker")

    @trace_span("reranker.rerank")
    def rerank(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank a list of chunks.
        
        Args:
            query: The user query
            chunks: List of chunk dicts (must have 'content')
            top_k: Number of results to return
            
        Returns:
            Reranked and sliced list of chunks with updated scores
        """
        if not self.reranker or not chunks:
            return chunks[:top_k]
        
        return self.reranker.rerank(query, chunks, top_k)

    def rrf_fuse(
        self, 
        vector_results: List[Dict[str, Any]], 
        graph_results: List[Dict[str, Any]], 
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) to combine Vector and Graph results.
        
        Formula: Score = 1.0 / (k + rank)
        """
        fused_scores = {}
        content_map = {}
        
        # Process Vector Results
        for rank, item in enumerate(vector_results):
            doc_id = item.get("id")
            if not doc_id: 
                continue
            
            content_map[doc_id] = item
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
            
        # Process Graph Results
        for rank, item in enumerate(graph_results):
            doc_id = item.get("id")
            if not doc_id: 
                continue
            
            if doc_id not in content_map:
                content_map[doc_id] = item
                
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
            
        # Sort by fused score
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        
        results = []
        for doc_id in sorted_ids:
            item = content_map[doc_id]
            item["score"] = fused_scores[doc_id] 
            results.append(item)
            
        return results


# Singleton
_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    """Get or create the reranker service singleton."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service

