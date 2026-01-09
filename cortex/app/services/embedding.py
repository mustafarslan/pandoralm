"""
Embedding Generation Service (High-Performance)
Creates vector embeddings using OpenAI, Ollama, or local models.

Performance Optimizations:
- Parallel batch processing with asyncio.gather()
- Configurable concurrency limits (EMBEDDING_CONCURRENCY)
- Semaphore-based rate limiting to prevent API overload
- Optimized Ollama parallel HTTP requests
"""
import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# Performance tuning via environment variables
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
EMBEDDING_CONCURRENCY = int(os.getenv("EMBEDDING_CONCURRENCY", "5"))
OLLAMA_EMBEDDING_BATCH_SIZE = int(os.getenv("OLLAMA_EMBEDDING_BATCH_SIZE", "50"))

# Thread pool for CPU-bound operations (SentenceTransformers)
_thread_pool: Optional[ThreadPoolExecutor] = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create shared thread pool for embedding operations."""
    global _thread_pool
    if _thread_pool is None:
        # Use CPU count for optimal parallelism
        max_workers = int(os.getenv("PANDORA_WORKER_THREADS", "0")) or os.cpu_count() or 4
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="embed_")
        logger.info(f"[Embedding] Created thread pool with {max_workers} workers")
    return _thread_pool


class EmbeddingProvider(str, Enum):
    """EmbeddingProvider types."""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    OLLAMA = "ollama"
    ONNX = "onnx"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = field(default_factory=lambda: EMBEDDING_BATCH_SIZE)
    concurrency: int = field(default_factory=lambda: EMBEDDING_CONCURRENCY)

    @classmethod
    def from_settings(cls) -> "EmbeddingConfig":
        """Create config from application settings."""
        provider_str = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        try:
            provider = EmbeddingProvider(provider_str)
        except ValueError:
            provider = EmbeddingProvider.OPENAI

        return cls(
            model=settings.DEFAULT_EMBEDDING_MODEL,
            provider=provider,
            batch_size=EMBEDDING_BATCH_SIZE,
            concurrency=EMBEDDING_CONCURRENCY,
        )


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding: List[float]
    tokens_used: int
    model: str


class EmbeddingService:
    """
    High-Performance Embedding Service for PandoraLM.

    Supports:
    - OpenAI embeddings (text-embedding-3-small/large, ada-002)
    - Sentence Transformers (local, CPU/GPU)
    - Ollama embeddings (local)
    - ONNX Runtime (accelerated local inference)

    Performance Features:
    - Parallel batch processing with asyncio.gather()
    - Semaphore-based concurrency limiting
    - Shared thread pool for blocking operations
    """

    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig.from_settings()
        self._openai_client = None
        self._sentence_transformer = None
        self._onnx_pipeline = None  # (model, tokenizer)
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        logger.info(
            f"[Embedding] Initialized: provider={self.config.provider.value}, "
            f"batch_size={self.config.batch_size}, concurrency={self.config.concurrency}"
        )

    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                raise ImportError("openai package not installed")
        return self._openai_client

    @property
    def sentence_transformer(self):
        """Lazy initialization of Sentence Transformer model."""
        if self._sentence_transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Auto-detect device (CUDA > MPS > CPU)
                device = os.getenv("COMPUTE_DEVICE", "auto")
                if device == "auto":
                    import torch
                    if torch.cuda.is_available():
                        device = "cuda"
                    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                        device = "mps"
                    else:
                        device = "cpu"
                logger.info(f"[Embedding] Loading SentenceTransformer on device: {device}")
                self._sentence_transformer = SentenceTransformer(self.config.model, device=device)
            except ImportError:
                raise ImportError("sentence-transformers package not installed")
        return self._sentence_transformer

    @property
    def onnx_pipeline(self):
        """Lazy initialization of ONNX Runtime model."""
        if self._onnx_pipeline is None:
            try:
                from transformers import AutoTokenizer
                from optimum.onnxruntime import ORTModelForFeatureExtraction
                import torch

                logger.info(f"[Embedding/ONNX] Loading model {self.config.model}")
                tokenizer = AutoTokenizer.from_pretrained(self.config.model)
                model = ORTModelForFeatureExtraction.from_pretrained(self.config.model, export=True)
                self._onnx_pipeline = (model, tokenizer)
            except ImportError as e:
                raise ImportError(f"ONNX/Optimum packages not installed: {e}")
            except Exception as e:
                 logger.error(f"[Embedding/ONNX] Failed to load model: {e}")
                 raise e
        return self._onnx_pipeline

    # =========================================================================
    # Public API
    # =========================================================================

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text."""
        results = await self.embed_texts([text])
        return results[0]

    async def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with parallel batch processing.

        This is the main entry point for high-performance embedding.
        Texts are split into batches and processed concurrently.
        """
        if not texts:
            return []

        if self.config.provider == EmbeddingProvider.OPENAI:
            return await self._embed_openai_parallel(texts)
        elif self.config.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            return await self._embed_sentence_transformers(texts)
        elif self.config.provider == EmbeddingProvider.OLLAMA:
            return await self._embed_ollama_parallel(texts)
        elif self.config.provider == EmbeddingProvider.ONNX:
            return await self._embed_onnx(texts)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")

    # =========================================================================
    # OpenAI Parallel Embedding
    # =========================================================================

    async def _embed_openai_parallel(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings using OpenAI API with parallel batch processing.

        Uses asyncio.gather() to process multiple batches concurrently,
        with semaphore-based rate limiting to prevent API overload.
        """
        # Split into batches
        batches = [
            texts[i:i + self.config.batch_size]
            for i in range(0, len(texts), self.config.batch_size)
        ]

        logger.info(f"[Embedding/OpenAI] Processing {len(texts)} texts in {len(batches)} batches (concurrency={self.config.concurrency})")

        # Process batches in parallel with semaphore limiting
        async def process_batch(batch: List[str]) -> List[EmbeddingResult]:
            async with self._semaphore:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    get_thread_pool(),
                    lambda: self.openai_client.embeddings.create(
                        input=batch,
                        model=self.config.model,
                    )
                )
                return [
                    EmbeddingResult(
                        embedding=item.embedding,
                        tokens_used=response.usage.total_tokens // len(batch),
                        model=self.config.model,
                    )
                    for item in response.data
                ]

        # Execute all batches concurrently
        batch_results = await asyncio.gather(*[process_batch(b) for b in batches])

        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)

        logger.info(f"[Embedding/OpenAI] Completed {len(results)} embeddings")
        return results

    # =========================================================================
    # Ollama Parallel Embedding
    # =========================================================================

    async def _embed_ollama_parallel(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings using Ollama with parallel HTTP requests.

        Ollama's /api/embeddings endpoint doesn't support batching,
        so we parallelize individual requests with semaphore limiting.
        """
        import httpx

        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        logger.info(f"[Embedding/Ollama] Processing {len(texts)} texts in parallel (concurrency={self.config.concurrency})")

        async def embed_single(client: httpx.AsyncClient, text: str) -> EmbeddingResult:
            async with self._semaphore:
                response = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={
                        "model": self.config.model,
                        "prompt": text,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()

                return EmbeddingResult(
                    embedding=data["embedding"],
                    tokens_used=0,
                    model=self.config.model,
                )

        # Process all texts in parallel with shared client
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(*[embed_single(client, text) for text in texts])

        logger.info(f"[Embedding/Ollama] Completed {len(results)} embeddings")
        return results

    # =========================================================================
    # SentenceTransformers (Local) Embedding
    # =========================================================================

    async def _embed_sentence_transformers(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings using Sentence Transformers.

        SentenceTransformers already handles batching internally,
        so we just run it in a thread pool to avoid blocking.
        """
        loop = asyncio.get_event_loop()

        logger.info(f"[Embedding/ST] Processing {len(texts)} texts with SentenceTransformers")

        # Run in thread pool (SentenceTransformers is synchronous)
        embeddings = await loop.run_in_executor(
            get_thread_pool(),
            lambda: self.sentence_transformer.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        )

        results = [
            EmbeddingResult(
                embedding=embedding.tolist(),
                tokens_used=0,
                model=self.config.model,
            )
            for embedding in embeddings
        ]

        logger.info(f"[Embedding/ST] Completed {len(results)} embeddings")
        return results

    # =========================================================================
    # ONNX Runtime (Accelerated Local) Embedding
    # =========================================================================

    async def _embed_onnx(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings using ONNX Runtime (via Optimum).

        Provides hardware-accelerated inference (CPU/AVX512 or GPU)
        for local models.
        """
        import torch
        loop = asyncio.get_event_loop()
        model, tokenizer = self.onnx_pipeline

        logger.info(f"[Embedding/ONNX] Processing {len(texts)} texts with ONNX Runtime")

        def _run_onnx_inference(batch_texts):
             # Tokenize
            inputs = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                return_tensors="pt"
            )

            # Run inference
            with torch.no_grad():
                outputs = model(**inputs)

            # Mean Pooling - Take attention mask into account for correct averaging
            token_embeddings = outputs.last_hidden_state
            attention_mask = inputs['attention_mask']

            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            embeddings = sum_embeddings / sum_mask

            return embeddings.tolist()

        # Run in thread pool
        # For very large datasets, we should batch manually here too,
        # but for typical ingestion chunks (100-500), one batch is often fine or handled by caller.
        # We obey EMBEDDING_BATCH_SIZE.

        all_embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            batch_embeddings = await loop.run_in_executor(
                 get_thread_pool(),
                 lambda: _run_onnx_inference(batch)
            )
            all_embeddings.extend(batch_embeddings)

        return [
            EmbeddingResult(
                embedding=emb,
                tokens_used=0,
                model=self.config.model,
            )
            for emb in all_embeddings
        ]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current embedding model."""
        model_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "dimensions": model_dims.get(self.config.model, self.config.dimensions),
            "batch_size": self.config.batch_size,
            "concurrency": self.config.concurrency,
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
