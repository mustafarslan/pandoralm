# Architecture Decision Record (ADR-004)

## Blue/Green Migration for Vector Stores on S3

### Context

PandoraLM uses LanceDB for vector storage. In production, this data resides on a MinIO (S3-compatible) bucket.
S3 is an object store, not a filesystem, so it does not support atomic directory renames.

### Problem

Migrating data (e.g., adding `layer_id` to schema) by renaming tables (`vectors` -> `vectors_backup`) is unsafe.
If the operation fails mid-way, the database enters a corrupted state.

### Solution: Blue/Green Migration

We adopt a Blue/Green strategy:

1. **Blue (Current)**: The application reads/writes to `vectors_workspace_id`.
2. **Green (New)**: A migration job creates `vectors_workspace_id_v2`.
3. **Migration Job**: Streams data from Blue to Green, applying schema transformations (e.g., setting `layer_id`).
4. **Verification**: The job verifies row counts match.
5. **Switchover**: Deployment configuration is updated to point to V2 tables (via Env Var or App Logic).

### Schema Update: Knowledge Layers

To support Multi-Tenancy, we added the following fields to `VectorChunk` and Neo4j Entities:

- `layer_id` (string): The partition/tenant ID.
- `access_roles` (list): RBAC roles allowed to view this datum.
- `visibility` (enum): `public`, `private`, `restricted`.

### JIT Security (Time-of-Check Time-of-Use)

To prevent security races, the Ingestion Worker now performs a **Just-In-Time (JIT)** check:

- Before embedding a document, it verifies the `user_id` still has WRITE access to the `layer_id`.
- This protects against cases where a user's access is revoked while a large file is sitting in the queue.
