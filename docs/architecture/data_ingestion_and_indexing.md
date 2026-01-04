# Data Ingestion & Indexing Pipeline

This document details how data (PDFs, Audio, Code) enters PandoraLM and is transformed into searchable intelligence.

## 1. The "Fast Lane" vs. "Heavy Lifting" Philosophy

To balance User Experience (UX) with Deep Intelligence, we use a two-tier architecture:

| Tier | Goal | Latency | Technology |
|------|------|---------|------------|
| **Fast Lane** | Make content searchable immediately | Seconds | Vector Embedding |
| **Heavy Lifting** | Understand relationships & themes | Minutes | GraphRAG (Entity Extraction) |

## 2. Ingestion Workflows

### A. Document Upload (PDF/Text)

1. **Upload:** User POSTs file to `pandora-core`.
2. **Proxy:** Node.js streams file directly to `pandora-cortex` (`/api/v1/ingest`).
    - *Why?* Prevents blocking the Node.js event loop with CPU-heavy tasks.
3. **Queueing:** Cortex saves file to `hotdir` and creates a status record in Postgres.
4. **Vectorization Task (Celery):**
    - **Extract:** Parses text from PDF.
    - **Chunk:** Splits text (512 tokens, 50 overlap).
    - **Embed:** Generates embeddings (OpenAI/Ollama).
    - **Store:** Writes to LanceDB (S3 backend).
    - **Status:** Marks document as `VECTOR_READY`.
5. **Graph Chaining:**
    - If Vectorization succeeds, it triggers `trigger_graph_indexing_task`.
    - **Rate Limit:** Capped at 5/minute to prevent API cost explosions.
    - **Indexing:** Extracts entities/relationships and updates Neo4j.

### B. Meeting Intelligence (Audio)

1. **Capture:** Headless browser bot captures audio stream.
2. **Stream to S3:** Audio is piped chunk-by-chunk to MinIO (`s3://pandora-audio/...`).
    - *Why?* K8s pods are ephemeral. If the bot crashes, we don't want to lose the file.
3. **Processing (GPU Worker):**
    - KEDA scales a GPU worker from 0 -> 1 when the Redis queue fills.
    - **Transcribe:** `faster-whisper`
    - **Diarize:** `pyannote.audio`
    - **Align:** Linear Scan algorithm merges "Speaker A" labels with transcribed text.
4. **Ingest:** Transcript chunks are indexed into LanceDB and Neo4j.

### C. Code Brain (Git Repos)

1. **Clone:** Worker clones repo to a **secure temporary volume** (`/tmp` or PVC).
2. **Parse (Tree-sitter):**
    - Instead of naive splitting, we walk the **Abstract Syntax Tree (AST)**.
    - We extract full `Class` and `Function` definitions.
3. **Graph Mapping:**
    - Relationships: `(:File)-[:CONTAINS]->(:Class)-[:HAS_METHOD]->(:Function)`
    - This creates a hierarchical map of the codebase structure.
4. **Cleanup:** Repo is deleted immediately to free storage.

## 3. Storage Internals

### Vector Store (LanceDB + S3)

We use **LanceDB** backed by **MinIO/S3**.

- **Files:** Data is stored as Parquet/Lance files in the object store.
- **Compute:** The Cortex API acts as the compute engine, reading/writing files over the network.
- **Benefit:** True separation of storage and compute. We can kill the API pod, and the data remains safe in S3.

### Knowledge Graph (Neo4j)

We use specific node labels for security:

- **Nodes:** `(:Entity {layer_id: "..."})`, `(:Document {layer_id: "..."})`
- **Edges:** `(:Entity)-[:RELATED_TO]->(:Entity)`
- **Optimization:** Community Detection (Leiden Algorithm) runs nightly to update summary nodes.
