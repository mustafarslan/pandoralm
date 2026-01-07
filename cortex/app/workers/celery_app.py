"""
Celery Application Configuration (High-Performance)
Background job processing for PandoraLM

Queue Architecture:
- fast_lane: Vectorization (seconds) - high concurrency, I/O bound
- embedding: Dedicated embedding queue (high throughput)
- heavy_lifting: GraphRAG (minutes/hours) - low concurrency, LLM bound
- audio_processing: GPU workers for transcription
- cron: Scheduled maintenance tasks (nightly)
"""
import os
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# =============================================================================
# High-Performance I/O Policy (Phase 8)
# =============================================================================
try:
    import uvloop
    import asyncio
    import os
    if os.getenv("ENABLE_UVLOOP", "false").lower() == "true":
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("🚀 [Celery] High-performance 'uvloop' event loop policy installed.")
    else:
        print("ℹ️  [Celery] 'uvloop' installed but disabled.")
except ImportError:
    pass

# =============================================================================
# Performance Tuning via Environment Variables
# =============================================================================

# Concurrency settings (adjust based on hardware)
FAST_LANE_PREFETCH = int(os.getenv("CELERY_FAST_LANE_PREFETCH", "4"))
EMBEDDING_PREFETCH = int(os.getenv("CELERY_EMBEDDING_PREFETCH", "8"))
HEAVY_LIFTING_PREFETCH = int(os.getenv("CELERY_HEAVY_LIFTING_PREFETCH", "1"))

# Memory management
MAX_TASKS_PER_CHILD = int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "50"))
MAX_MEMORY_PER_CHILD = int(os.getenv("CELERY_MAX_MEMORY_PER_CHILD_KB", "0")) or None  # 0 = disabled

celery_app = Celery(
    "pandora_cortex",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.indexing",
        "app.workers.tasks.research",
        "app.workers.tasks.vector_ops",
        "app.workers.tasks.graph_ops",
        "app.workers.tasks.cron",
        "app.workers.tasks.scraper",
        "app.workers.tasks.audio",  # Phase 5.4: Meeting Intelligence
        "app.workers.tasks.memory_consolidation", # Memory maintenance
    ],
)

# =============================================================================
# Celery Configuration
# =============================================================================

celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600 * 24,  # 24 hours
    
    # =========================================================================
    # OPTIMIZED: Queue Routing for High-Throughput Ingestion
    # =========================================================================
    task_routes={
        # Fast Lane - Vectorization (seconds, high concurrency)
        # These tasks use asyncio internally for parallel I/O
        "indexing.vectorize_document": {"queue": "fast_lane"},
        
        # Embedding Queue - Dedicated high-throughput embedding
        # Optimized for parallel batch embedding tasks
        "indexing.embed_batch": {"queue": "embedding"},
        "indexing.embed_chunks": {"queue": "embedding"},
        
        # Heavy Lifting - GraphRAG (minutes/hours, low concurrency)
        # Rate-limited to prevent LLM token burn
        "indexing.start_graph_indexing": {"queue": "heavy_lifting"},
        "indexing.trigger_graph_indexing": {"queue": "heavy_lifting"},
        "indexing.extract_entities_batch": {"queue": "heavy_lifting"},
        "indexing.combine_and_store": {"queue": "heavy_lifting"},
        
        # Audio Processing - GPU accelerated (Phase 5.4)
        "audio.process_audio": {"queue": "audio_processing"},
        "audio.health_check": {"queue": "audio_processing"},
        
        # Cron tasks - scheduled maintenance
        "cron.regenerate_stale_communities": {"queue": "cron"},
        "cron.trigger_community_regeneration": {"queue": "cron"},
        "cron.purge_old_chat_messages": {"queue": "cron"},
        
        # Default queues for other tasks
        "app.workers.tasks.indexing.*": {"queue": "indexing"},
        "app.workers.tasks.research.*": {"queue": "research"},
    },
    
    # =========================================================================
    # OPTIMIZED: Queue Definitions with Priorities
    # =========================================================================
    task_queues={
        # High priority - immediate user feedback
        "fast_lane": {"exchange": "fast_lane", "routing_key": "fast_lane"},
        "embedding": {"exchange": "embedding", "routing_key": "embedding"},
        
        # Default priority - background processing
        "heavy_lifting": {"exchange": "heavy_lifting", "routing_key": "heavy_lifting"},
        "indexing": {"exchange": "indexing", "routing_key": "indexing"},
        "research": {"exchange": "research", "routing_key": "research"},
        
        # Low priority - maintenance
        "cron": {"exchange": "cron", "routing_key": "cron"},
        "audio_processing": {"exchange": "audio_processing", "routing_key": "audio_processing"},
    },
    
    # =========================================================================
    # OPTIMIZED: Concurrency & Prefetch Settings
    # =========================================================================
    
    # Prefetch multiplier: Higher = more tasks grabbed at once
    # For embedding tasks (I/O bound), higher prefetch improves throughput
    # For GraphRAG (CPU/LLM bound), keep at 1 to prevent memory issues
    worker_prefetch_multiplier=FAST_LANE_PREFETCH,
    
    # Acknowledge after completion for reliability
    task_acks_late=True,
    
    # =========================================================================
    # OPTIMIZED: Memory Management
    # =========================================================================
    
    # Recycle workers after N tasks to prevent memory leaks
    worker_max_tasks_per_child=MAX_TASKS_PER_CHILD,
    
    # Kill workers that exceed memory limit (if set)
    worker_max_memory_per_child=MAX_MEMORY_PER_CHILD,
    
    # =========================================================================
    # Retry & Time Limit Settings
    # =========================================================================
    
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Increased time limits for large document processing
    task_time_limit=3600 * 4,  # 4 hours max for any task
    task_soft_time_limit=3600 * 2,  # 2 hour soft limit
    
    # =========================================================================
    # Beat Scheduler for Periodic/Cron Tasks
    # =========================================================================
    beat_schedule={
        # Nightly community summarization (3 AM UTC)
        "regenerate-stale-communities-nightly": {
            "task": "cron.regenerate_stale_communities",
            "schedule": crontab(hour=3, minute=0),
            "kwargs": {},
        },
        # Chat message retention purge (4 AM UTC)
        "purge-old-chat-messages-nightly": {
            "task": "cron.purge_old_chat_messages",
            "schedule": crontab(hour=4, minute=0),
            "kwargs": {},
        },
        # Memory maintenance (5 AM UTC)
        "trigger-memory-maintenance-daily": {
            "task": "cron.trigger_memory_maintenance",
            "schedule": crontab(hour=5, minute=0),
            "kwargs": {},
        },
    },
)


if __name__ == "__main__":
    celery_app.start()
