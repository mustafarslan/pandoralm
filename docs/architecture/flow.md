# Life of a Query: From Input to Insight

This document explains exactly "HOW" PandoraLM processes a user request, step-by-step.

## 1. The Interaction (Frontend -> Backend)

1. **User Input:** The user types a message or clicks a "Meeting Reference" in the UI.
2. **Streaming Request:** The frontend initiates a POST request to `/api/v1/stream/chat`.
    - **Protocol:** Vercel AI SDK Data Stream Protocol.
    - **Format:** The response streams chunks like `0:"text"` (content) and `2:[{"type":"thought"}]` (intermediate reasoning).

## 2. The Caching Layer (Zero-Latency)

Before even thinking, the system checks its short-term memory (Redis).

- **Prompt Cache:**
  - **Key:** `SHA256(System Prompt + Sorted(Chunk IDs) + Query)`
  - **Logic:** If the *exact same context* (same retrieved documents) matches a previous query, return the cached answer immediately.
  - **Why?** Reduces Latency and LLM API costs for repetitive questions or identical RAG contexts.

## 3. The Cognitive Router (Decision Making)

Before searching for data, Cortex must decide *how* to think. This is the **Tiered Inference** architecture.

### Tier 1: Semantic Routing (<50ms)

- **Mechanism:** Local embedding similarity (`all-MiniLM-L6-v2`).
- **Logic:** Does the query strictly match a predefined route?
  - "Fix the bug in main.py" -> **Codebase Route**
  - "Search for latest news" -> **Web Research Route**
- **Outcome:** If confident (>0.8), skip LLM and go straight to execution.

### Tier 2: The 1B Classifier (<300ms)

- **Mechanism:** If Semantic Router is unsure, we call a small, fast LLM (`gemma3:1b`).
- **Prompt:** "You are a JSON classifier. Output `{intent: 'FACTUAL'|'THEMATIC'}`."
- **Why?** Avoids wasting money/time on a Reasoning Model for simple questions like "What is the IP address?".

## 4. The Execution Paths

Based on the intent, the system forks:

### Path A: 'FACTUAL' (System 1 - Fast)

*Goal: Precise retrieval of specific facts.*

1. **Vector Search:** Query LanceDB for similar chunks.
    - **Filter:** `WHERE layer_id IN [user_authorized_layers] (Pre-filtering)`.
2. **Reranking:** Pass top 50 results to **Cross-Encoder**.
    - Scores relevance of `(Query, Document)` pairs.
    - Trims to Top 10.
3. **Synthesis:** LLM answers using the context.

### Path B: 'THEMATIC' (System 2 - Slow)

*Goal: Connecting dots across many documents.*

1. **Global Search:** Query Neo4j and LanceDB.
    - **Community Summaries:** Instead of raw text, we search pre-generated *summaries* of document clusters (Leiden Communities).
    - "Tell me about Project X" matches the *Community Summary* for "Project X Team", even if the exact keyword differs.
2. **Graph Expansion:**
    - Extract entities from query.
    - Traverse up to 2 hops in Neo4j to find related entities.

### Path C: 'CODE_GENERATION' (The Code Brain)

*Goal: Understanding software architecture.*

1. **Hybrid Retrieval:**
    - **Sparse (BM25):** Matches exact function names (`process_payment`).
    - **Dense (Vector):** Matches intent ("handling credit cards").
2. **Context Expansion:**
    - If a `Function` node is found, the system queries the Graph to pull in the parent `Class` and the `File` path.
    - This provides the LLM with the *scope* it needs to write correct code.

## 5. Response Streaming (The Output)

The response is constructed incrementally to keep the user engaged.

- **Phase 1: Thoughts (Blue Accordion)**
  - "Searching knowledge graph..." (Streamed as data event `2:`)
  - "Reading specific file..."
- **Phase 2: The Answer**
  - Standard text generation.
- **Phase 3: Interactive Triggers (Generative UI)**
  - If the answer references a meeting, the backend injects a **Meeting Trigger**:
      `2:[{"type": "meeting_ref", "fileId": "123", "timestamp": 450}]`
  - The UI sees this and immediately renders a clickable **Meeting Player** component.
