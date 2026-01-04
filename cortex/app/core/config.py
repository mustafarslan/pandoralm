"""
Pydantic Settings for Pandora Cortex
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]
    DEV_MODE_SKIP_AUTH: bool = True

    # Neo4j (Graph Database)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "pandora123"

    # LanceDB (Vector Database)
    LANCEDB_PATH: str = "./storage/lancedb"  # Local fallback
    LANCEDB_URI: str = ""  # S3 URI (e.g. s3://pandora-vectors)
    AWS_ENDPOINT_URL: str = ""  # For MinIO
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    LANCEDB_TABLE: str = "vectors" # Table name (e.g. vectors vs vectors_v2)

    # Object Storage
    S3_BUCKET_AUDIO: str = "pandora-audio"
    S3_BUCKET_DOCS: str = "pandora-docs"
    S3_REGION_NAME: str = "us-east-1"


    # Search & Reranking
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ENABLE_RERANKING: bool = True

    # Redis (Celery Broker)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_ROUTES: dict = {
        "process_document": {"queue": "ingest"},
        "perform_scrape_task": {"queue": "scraper"},
        "process_audio_task": {"queue": "audio_gpu"},
        "consolidate_memory": {"queue": "memory"},
    }

    # PostgreSQL
    DATABASE_URL: str = "postgresql://pandora:pandora@localhost:5432/pandora"

    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8080"  # Internal/Docker URL
    KEYCLOAK_PUBLIC_URL: str = "http://localhost:8080"  # Browser-accessible URL
    KEYCLOAK_REALM: str = "pandora"
    KEYCLOAK_CLIENT_ID: str = "pandora-cortex"
    KEYCLOAK_CLIENT_SECRET: str = ""

    # LLM Settings
    OPENAI_API_KEY: str = ""
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    
    # Tiered Inference Settings (Router = fast classifier, Solver = heavy reasoning)
    # Router: Fast model for query classification (<300ms target)
    # Solver: Heavy reasoning model for complex generation (5-60s)
    LLM_PROVIDER: str = "ollama"  # "openai" or "ollama"
    LLM_ROUTER_MODEL: str = "gemma3:1b"  # Fast classification model
    LLM_SOLVER_MODEL: str = "deepseek-r1:8b"  # Complex reasoning model
    LLM_ROUTER_API_BASE: str = "http://host.docker.internal:11434"
    LLM_SOLVER_API_BASE: str = "http://host.docker.internal:11434"
    
    # Legacy settings (deprecated, kept for backward compatibility)
    ROUTER_LLM_PROVIDER: str = "ollama"  # Use LLM_PROVIDER instead
    ROUTER_LLM_MODEL: str = "gemma3:1b"  # Use LLM_ROUTER_MODEL instead
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"  # Use LLM_ROUTER_API_BASE instead
    OLLAMA_MODEL: str = "deepseek-r1:8b"  # Use LLM_SOLVER_MODEL instead

    # GraphRAG
    GRAPHRAG_CACHE_DIR: str = "./storage/graphrag"
    # Use a faster model for GraphRAG entity extraction (not reasoning model)
    # json output works better with non-reasoning models for structured extraction
    LLM_GRAPHRAG_MODEL: str = "gemma3:4b"  # faster than deepseek-r1 for extraction

    # ===============================
    # Phase 5-2: Cognitive Core
    # ===============================
    
    # Memory Service (Mem0)
    ENABLE_MEMORY: bool = True
    MEMORY_BACKEND: str = "lancedb"
    
    # Memory LLM Provider: "openai" or "ollama"
    # User can choose which LLM to use for fact extraction
    MEMORY_LLM_PROVIDER: str = "openai"  # "openai" or "ollama"
    MEMORY_LLM_MODEL: str = "gpt-4o-mini"  # OpenAI model or Ollama model name
    MEMORY_OLLAMA_URL: str = "http://host.docker.internal:11434"  # Ollama server URL
    
    # Memory Embedder Provider: "openai" or "ollama"
    MEMORY_EMBEDDER_PROVIDER: str = "openai"  # "openai" or "ollama"
    MEMORY_EMBEDDER_MODEL: str = "text-embedding-3-small"  # OpenAI or Ollama embedding model
    
    MEMORY_SEARCH_LIMIT: int = 5
    
    # Prompt Caching
    ENABLE_PROMPT_CACHE: bool = True
    PROMPT_CACHE_TTL: int = 3600  # 1 hour
    
    # Reranker Provider (local = CrossEncoder, cohere = Cohere API)
    RERANKER_PROVIDER: str = "local"  # "local" or "cohere"
    COHERE_API_KEY: str = ""

    # ===============================
    # High-Performance Ingestion
    # ===============================
    
    # Embedding Performance
    EMBEDDING_BATCH_SIZE: int = 100  # Texts per batch for OpenAI/SentenceTransformers
    EMBEDDING_CONCURRENCY: int = 5   # Concurrent API calls / batches
    OLLAMA_EMBEDDING_BATCH_SIZE: int = 50  # Texts per parallel request pool
    
    # GraphRAG Performance
    GRAPHRAG_BATCH_SIZE: int = 20    # Chunks per entity extraction batch
    GRAPHRAG_CONCURRENCY: int = 3    # Concurrent LLM calls for extraction
    
    # Worker Configuration (0 = auto-detect based on CPU cores)
    PANDORA_WORKER_THREADS: int = 0
    PANDORA_WORKER_PROCESSES: int = 0
    
    # Cross-Platform Compute Device ("auto", "cpu", "cuda", "mps")
    COMPUTE_DEVICE: str = "auto"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
