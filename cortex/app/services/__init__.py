"""
Services Package
Business logic and data access services
"""
try:
    from app.services.vector_store import LanceDBStore, VectorChunk, SearchResult, get_vector_store
except ImportError:
    # Allow partial loading for testing when lancedb/numpy is not installed
    pass
try:
    from app.services.chunking import TextChunker, ChunkConfig, ChunkPreview, SplitterType, get_chunker
except ImportError:
    pass

try:
    from app.services.embedding import EmbeddingService, EmbeddingConfig, EmbeddingResult, get_embedding_service
except ImportError:
    pass

try:
    from app.services.vram_calculator import VRAMCalculator, VRAMEstimate, Precision, get_vram_calculator
except ImportError:
    pass

try:
    from app.services.document_parser import DocumentParser, ParsedDocument, DocumentFormat, get_document_parser
except ImportError:
    pass
from app.services.router import (
    IntentType,
    ClassificationResult,
    QueryIntentClassifier,
    get_intent_classifier,
    INTENT_TO_QUERY_MODE,
)

__all__ = [
    # Vector Store
    "LanceDBStore",
    "VectorChunk",
    "SearchResult",
    "get_vector_store",
    
    # Chunking
    "TextChunker",
    "ChunkConfig",
    "ChunkPreview",
    "SplitterType",
    "get_chunker",
    
    # Embedding
    "EmbeddingService",
    "EmbeddingConfig",
    "EmbeddingResult",
    "get_embedding_service",
    
    # VRAM Calculator
    "VRAMCalculator",
    "VRAMEstimate",
    "Precision",
    "get_vram_calculator",
    
    # Document Parser
    "DocumentParser",
    "ParsedDocument",
    "DocumentFormat",
    "get_document_parser",
    
    # Cognitive Router
    "IntentType",
    "ClassificationResult", 
    "QueryIntentClassifier",
    "get_intent_classifier",
    "INTENT_TO_QUERY_MODE",
]
