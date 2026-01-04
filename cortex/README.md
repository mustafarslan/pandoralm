# Pandora Cortex

Heavy compute engine for PandoraLM - handling GraphRAG indexing, embeddings, and deep research.

## Tech Stack

- **FastAPI** - Async API framework
- **Celery + Redis** - Background job processing
- **LanceDB** - Vector database (embedded)
- **Neo4j** - Graph database
- **GraphRAG** - Microsoft's knowledge graph RAG

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload --port 8000

# Run Celery worker
poetry run celery -A app.workers.celery_app worker --loglevel=info

# Run tests
poetry run pytest
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/ingest/*` - Document ingestion
- `GET /api/v1/vectors/*` - Vector operations
- `POST /api/v1/graph/*` - GraphRAG operations
- `POST /api/v1/research/*` - Deep research
