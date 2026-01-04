# PandoraLM End-to-End Testing

This suite uses **Playwright** and **Pytest** to verify the end-to-end functionality of PandoraLM, specifically focusing on the "Hybrid Brain" architecture (Core UI + Cortex Backend).

## Prerequisites

- Docker stack running (`docker-compose up -d`)
- Python 3.11+
- `pip install pytest pytest-playwright`
- `playwright install chromium`

## Test Scenarios

### 1. The Ingestion Pipeline (`test_ingestion_flow.py`)

**Goal:** Verify that a PDF upload traverses the entire architecture correctly.

1. **Login**: Authenticates as `admin`.
2. **Upload**: Uploads `fixtures/small.pdf` via Admin Console.
3. **Verification (UI)**: Checks `Vector Inspector` for correct chunk count (should not be 0).
4. **Verification (Backend)**: Polls `Cortex` API to confirm persistence.

### 2. The Cognitive Router (`test_inference.py`)

**Goal:** Verify System 1 vs System 2 routing (Mocked LLM).

1. **Fast Query**: "What is the capital of France?" -> Should trigger Vector Search (Green Bar).
2. **Slow Query**: "Compare the compliance policies of A vs B" -> Should trigger Graph Search (Blue Bar).

### 3. Agentic Tools (`test_mcp.py`)

**Goal:** Verify MCP tool execution.

1. **Tool Call**: "Search google for X" -> Should show "Thinking..." and tool output.

## Running Tests

```bash
# Run all tests
pytest tests/e2e/

# Run specific test (Ingestion)
pytest tests/e2e/test_ingestion_flow.py
```
