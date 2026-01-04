# Architectural Decisions Log (ADR)

This document records the critical architectural choices made during the development of PandoraLM, explaining the "WHY" behind the "HOW".

## 1. Hub-and-Spoke Architecture

**Decision:** Split the existing monolith into `Pandora Core` (Node.js) and `Pandora Cortex` (Python).

- **Why:** The original Node.js backend was struggling with heavy CPU tasks (chunking, embedding). Node.js is single-threaded and optimized for I/O, not Compute.
- **Benefit:** We can scale the Python "Brain" independently of the Node.js "Face". We can deploy Cortex on GPU nodes while keeping Core on cheap CPU nodes.

## 2. Tiered Inference (The Cognitive Router)

**Decision:** Do not send every query to GPT-4/DeepSeek-R1. Use a hierarchy of models.

- **Why:** Sending "What is the capital of France?" to a Reasoning Model (System 2) is wasteful (cost & latency).
- **Implementation:**
  - **Tier 0:** Semantic Router (Embeddings) - Instant (<50ms).
  - **Tier 1:** 1B Parameter Router (Gemma) - Fast (<300ms).
  - **Tier 2:** Solver (DeepSeek/GPT-4) - Powerful.
- **Benefit:** 70% cost reduction and perceived latency improvement.

## 3. Distributed Agents via MCP Bridge

**Decision:** Wrap standard MCP (Model Context Protocol) servers in a Networked SSE Bridge.

- **Why:** The standard MCP spec relies on `stdio` (parent process spawns child process). In Kubernetes, this is an anti-pattern (Sidecars are complex, dependencies bloat the main container).
- **Benefit:** We can run "Google Search Agent" as a totally separate microservice. If it crashes, it doesn't take down the main API.

## 4. ReBAC (Relationship-Based Access Control)

**Decision:** Enforce security at the Database Layer (`layer_id`), not just in the Application Logic.

- **Why:** "Application-level filtering" is prone to bugs. If a developer forgets an `if` statement, data leaks.
- **Implementation:** Every Vector Search *automatically* injects a `WHERE layer_id IN (...)` filter clause.
- **Benefit:** Defense-in-depth. Even if the UI shows a link to a forbidden document, the database will return 0 results.

## 5. LanceDB on S3 (The Data Lakehouse)

**Decision:** Use LanceDB with an S3 backend instead of a stateful vector DB (like Chroma/Milvus) or local disk.

- **Why:** Managing stateful databases in K8s is hard. Using S3 allows us to treat the vector index as "Blob Data".
- **Benefit:** "Serverless" architecture. We can spin up 10 Cortex replicas reading from the same S3 bucket without complex synchronization logic.

## 6. UI Architecture Overhaul (Knowledge OS)

**Decision:** Replace legacy "AnythingLLM" sidebar with a Unified "Active Context" Navigation Rail.

- **Why:** The legacy sidebar was purely navigational (HTML anchors), leading to full page reloads and loss of state. It also conflicted with the new "Concept of Layers" (ReBAC).
- **Implementation:**
  - **UnifiedSidebar:** A single React component managing multiple views (Layers, Library, Settings).
  - **ActiveContextPanel:** A dedicated UI for visualizing the user's security context (System, Org, Team, User).
  - **Dynamic Branding:** Theme-aware logo rendering to support the "Neo-Dark" aesthetic.
- **Benefit:** Eliminates "Ghost Space" layout bugs, improves perceived performance (SPA navigation), and reinforces the security model visually.

## 7. Blue/Green Migration Strategy

**Decision:** Use table swapping (`vectors` vs `vectors_v2`) instead of in-place schema changes for Vector indices.

- **Why:** Re-indexing vectors takes hours. We cannot have downtime in an enterprise environment.
- **Implementation:**
  1. Workers write to a new, disconnected table (`vectors_v2`).
  2. Once complete, update `LANCEDB_TABLE` environment variable.
  3. Rolling restart of Cortex pods switches traffic instantly.
- **Benefit:** Zero-downtime upgrades for embedding model changes.

## 8. Lazy Graph Summarization

**Decision:** Do not run Leiden Community Detection on every document upload. Run it nightly.

- **Why:** Community detection is O(N^2) relative to graph size. Running it per-document is computationally prohibitive and creates race conditions.
- **Implementation:**
  - **Single Doc:** Updates nodes/edges immediately.
  - **Nightly Job:** Runs `algo.community.leiden` to cluster nodes and generate high-level summaries.
- **Benefit:** Keeps ingestion latency low (seconds) while still providing "Global Search" capabilities (eventual consistency).
