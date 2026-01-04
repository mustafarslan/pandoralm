### Why Asyncio over Celery Groups? (Phase 4 Refactor)

**Problem**: Traditional distributed task queues (Celery Groups/Chords) introduce huge network overhead when passing large vector payloads (1000s of chunks) between workers and the broker (Redis).

**Solution**: **Vertical Asyncio Scaling** + **Horizontal KEDA Scaling**

| Metric | Celery Groups (Map-Reduce) | Asyncio (Pandora Pattern) | Why? |
|--------|----------------------------|---------------------------|------|
| **Throughput** | ~8 docs/sec | **~86 docs/sec** | Zero-Copy in-memory processing avoids serialization |
| **Network** | Heavy (Payloads -> Redis) | **Minimal** (Only Job ID) | Vectors stay in RAM until final DB write |
| **Complexity** | High (Synchronization) | **Low** (Single Event Loop) | No "Chord Barrier" synchronization stalls |

We use **KEDA** to scale the number of *Asyncio Workers*, rather than using Celery to split a *single document* across workers. This "Document-Parallel" approach is O(N) efficient vs "Chunk-Parallel" O(N*Network).
