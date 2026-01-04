
# =============================================================================
# PandoraLM Ingestion Benchmark
# Measures throughput of Parallel Chunking and Embedding Engine
# =============================================================================
import asyncio
import time
import os
import sys
import random
import string
from typing import List

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.embedding import get_embedding_service, EmbeddingConfig
from app.services.chunking import chunk_text_parallel, get_process_pool
from app.core.config import settings

# Configuration
NUM_DOCS = 100
DOC_LENGTH = 5000  # Characters (approx 1000 tokens)
WARMUP = True

def generate_random_text(length: int) -> str:
    """Generate random text content."""
    return ''.join(random.choices(string.ascii_letters + " " * 10 + "\n", k=length))

async def run_benchmark():
    print(f"🚀 PANDORALM PERFORMANCE BENCHMARK")
    print(f"===================================")
    print(f"Device: {settings.COMPUTE_DEVICE}")
    print(f"Workers: {settings.PANDORA_WORKER_PROCESSES} processes, {settings.PANDORA_WORKER_THREADS} threads")
    print(f"Docs: {NUM_DOCS}, Length: {DOC_LENGTH} chars")
    print(f"-----------------------------------")

    # Generate Data
    print(f"📝 Generating {NUM_DOCS} synthetic documents...")
    docs = [generate_random_text(DOC_LENGTH) for _ in range(NUM_DOCS)]
    total_chars = sum(len(d) for d in docs)
    print(f"   Total Size: {total_chars / 1024 / 1024:.2f} MB")
    
    # ---------------------------------------------------------
    # Benchmark 1: Parallel Chunking (Process Pool)
    # ---------------------------------------------------------
    print(f"\n⚡ Benchmarking Parallel Chunking...")
    start_time = time.time()
    
    # Run chunking in parallel
    tasks = [
        chunk_text_parallel(text=doc, chunk_size=1000, chunk_overlap=200)
        for doc in docs
    ]
    chunk_results = await asyncio.gather(*tasks)
    
    # Flat list of all chunks
    all_chunks = []
    for chunks in chunk_results:
        all_chunks.extend([c["content"] for c in chunks])
        
    chunking_time = time.time() - start_time
    print(f"   Time: {chunking_time:.4f} s")
    print(f"   Throughput: {len(docs) / chunking_time:.2f} docs/s")
    print(f"   Total Chunks: {len(all_chunks)}")

    # ---------------------------------------------------------
    # Benchmark 2: Parallel Embedding (Async Batching)
    # ---------------------------------------------------------
    service = get_embedding_service()
    print(f"\n🧠 Benchmarking Parallel Embedding ({service.config.provider.value})...")
    print(f"   Model: {service.config.model}")
    print(f"   Batch Size: {service.config.batch_size}, Concurrency: {service.config.concurrency}")
    
    # Warmup
    if WARMUP:
        print("   Warming up model...")
        await service.embed_texts(["warmup " * 10])
    
    start_time = time.time()
    
    # Embed all chunks
    embeddings = await service.embed_texts(all_chunks)
    
    embedding_time = time.time() - start_time
    total_tokens = sum(e.tokens_used for e in embeddings) if embeddings else 0
    # Estimate tokens if provider returns 0 (local models)
    if total_tokens == 0:
        total_tokens = sum(len(c.split()) * 1.3 for c in all_chunks)
        
    print(f"   Time: {embedding_time:.4f} s")
    print(f"   Throughput: {len(all_chunks) / embedding_time:.2f} chunks/s")
    print(f"   Throughput: {total_tokens / embedding_time:.2f} tokens/s")
    
    print(f"\n✅ Benchmark Complete")

if __name__ == "__main__":
    # Use uvloop if available
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass
        
    asyncio.run(run_benchmark())
