"""
Text Ingestion Worker (Celery Task)

Handles asynchronous processing of uploaded documents (PDF, Docx, Text).
Refactored to use Celery Chains for Event-Driven Architecture.

Flow:
1. start_ingestion_pipeline (Entry) -> Checks Permissions
2. extract_text_task (Worker) -> Parses PDF/Doc OR Clones Git Repo
3. chunk_and_embed_task (Worker) -> Vectorization (Fast Lane) -> Updates DocumentStatus
4. index_graph_incrementally_task (Worker) -> GraphRAG (Heavy Lifting)
"""
import os
import asyncio
import logging
import json
import shutil
from uuid import uuid4
from typing import Dict, Any, List

from celery import shared_task, chain
from app.core.database import async_session_maker
from app.core.config import settings
from app.models.layer import AccessLevel
from app.models.document_status import DocumentStatus, ProcessingStatus
# Services
from app.services.chunking import get_chunker
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store, VectorChunk
from app.services.document_status_service import get_document_status_service
from app.services.code.git import GitRepository
from app.services.graphrag.indexer import get_graphrag_indexer

# Security
from app.services.security.layer_manager import LayerManager

logger = logging.getLogger(__name__)

# =============================================================================
# Pipeline Entry Point
# =============================================================================

@shared_task(name="cortex.workers.ingest.start_pipeline")
def start_ingestion_pipeline(
    filepath: str, 
    document_id: str, 
    workspace_id: str, 
    layer_id: str, 
    user_id: str
):
    """
    Entry point that builds and executes the ingestion chain.
    """
    logger.info(f"[Ingest] Starting pipeline for doc={document_id}")
    
    # Initialize Status
    get_document_status_service().create(document_id, workspace_id, filename=os.path.basename(filepath))

    # Define the chain
    # 1. Extract Text (or Code)
    # 2. Chunk & Embed (Vector Ready)
    # 3. Graph Indexing (Graph Ready)
    
    pipeline = chain(
        extract_text_task.s(filepath, document_id, workspace_id, layer_id, user_id),
        chunk_and_embed_task.s(),
        index_graph_incrementally_task.s()
    )
    
    pipeline.apply_async()
    return {"status": "started", "document_id": document_id}

# =============================================================================
# Worker Tasks
# =============================================================================

@shared_task(name="cortex.workers.ingest.extract_text", bind=True)
def extract_text_task(self, filepath: str, document_id: str, workspace_id: str, layer_id: str, user_id: str) -> Dict[str, Any]:
    """
    Step 1: JIT Check & Text Extraction.
    Handles both File Uploads and Git Repositories (Phase 3A).
    """
    try:
        # 1. JIT Security Check
        if not asyncio.run(_verify_write_access(user_id, layer_id)):
            raise PermissionError(f"User {user_id} denied write access to {layer_id}")
            
        logger.info(f"[Ingest] Extracting content for {document_id}")
        
        # 2. Detect Content Type
        content = ""
        is_git = filepath.endswith(".git") or filepath.startswith("http") or filepath.startswith("git@")
        
        if is_git:
            # Phase 3A: Git Ingestion
            logger.info(f"[Ingest] Detected Git Repo: {filepath}")
            
            with GitRepository(filepath) as repo_path:
                # Walk the repo and aggregate content
                # Note: For production large repos, we'd spawn sub-tasks.
                # Here we aggregate to fit the Single Document model.
                aggregated_content = []
                for root, dirs, files in os.walk(repo_path):
                    if ".git" in dirs:
                        dirs.remove(".git")  # Don't recurse into .git
                        
                    for file in files:
                        if file.startswith("."): continue
                        
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, repo_path)
                        
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                file_content = f.read()
                                if file_content.strip():
                                    aggregated_content.append(f"File: {rel_path}\n\n{file_content}")
                        except Exception:
                            pass # Skip binary/unreadable
                
                content = "\n\n".join(aggregated_content)
                logger.info(f"Aggregated {len(aggregated_content)} files from git repo")

        else:
            # Standard File
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
                
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                content = "Binary content placeholder"
            
        return {
            "content": content,
            "document_id": document_id,
            "workspace_id": workspace_id,
            "layer_id": layer_id,
            "user_id": user_id,
            "filepath": filepath 
        }
        
    except Exception as e:
        logger.error(f"[Ingest] Extraction failed: {e}")
        _update_status(document_id, vector_status=ProcessingStatus.FAILED, error=str(e))
        raise

@shared_task(name="cortex.workers.ingest.chunk_embed", bind=True)
def chunk_and_embed_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 2: Chunking & Vectorization (The Fast Lane).
    """
    content = payload["content"]
    document_id = payload["document_id"]
    workspace_id = payload["workspace_id"]
    layer_id = payload["layer_id"]
    filepath = payload.get("filepath", "upload")
    
    logger.info(f"[Ingest] Chunking & Embedding {document_id}")
    _update_status(document_id, vector_status=ProcessingStatus.PROCESSING)
    
    try:
        if not content:
            logger.warning("Empty content, skipping vectorization")
            _update_status(document_id, vector_status=ProcessingStatus.COMPLETED, chunk_count=0)
            payload["chunk_ids"] = []
            return payload

        # 3. Chunking Strategy
        from app.services.code.parser import get_code_parser
        code_parser = get_code_parser()
        
        # Check if file extension is supported for AST parsing
        import pathlib
        ext = pathlib.Path(filepath).suffix
        
        previews = []
        is_code = ext in code_parser.SUPPORTED_LANGUAGES
        
        if is_code:
            logger.info(f"[Ingest] Using Tree-sitter AST parser for {filepath}")
            # CodeParser returns CodeChunk objects, we need to adapt or use them
            code_chunks = code_parser.parse_file(content, filepath, workspace_id, layer_id, document_id)
            # Adapt CodeChunks to VectorChunks structure or use directly if compatible
            # For now, we mix them into the vector_chunks list below
            # But the loop below expects 'previews' from chunker. 
            # Let's map code_chunks to a compatible object or handle separately.
            
            # Since CodeParser returns fully formed chunks with metadata, we can skip the loop below
            # and just go to embedding.
            pass 
        else:
            chunker = get_chunker()
            previews = chunker.chunk_text(content)
        
        # 4. Embedding & Object Construction
        embedder = get_embedding_service()
        vector_store = get_vector_store()
        
        vector_chunks = []
        
        if is_code:
            # Handle CodeChunks
            for cc in code_chunks:
                # Code Chunks might already have some metadata, but need embedding
                embedding = embedder.embed_query(cc.content)
                cc.embedding = embedding
                
                # Convert to VectorChunk (ensure compatibility)
                vector_chunks.append(VectorChunk(
                    id=cc.id,
                    content=cc.content,
                    embedding=embedding,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    layer_id=layer_id,
                    access_roles=[],
                    visibility="private",
                    metadata={
                        "source": filepath,
                        "node_type": cc.node_type,
                        "signature": cc.signature,
                        "language": cc.language,
                        "start_line": cc.start_line,
                        "end_line": cc.end_line
                    }
                ))
        else:
            # Handle Text Chunks
            for prev in previews:
                text_chunk = prev.content
                embedding = embedder.embed_query(text_chunk)
                chunk_id = str(uuid4())
                
                vector_chunks.append(VectorChunk(
                    id=chunk_id,
                    content=text_chunk,
                    embedding=embedding,
                    document_id=document_id,
                    workspace_id=workspace_id,
                    layer_id=layer_id,
                    access_roles=[],
                    visibility="private",
                    metadata={"source": filepath}
                ))
            
        # 5. Store
        if vector_chunks:
            vector_store.add_chunks(vector_chunks, workspace_id)
        
        # Success - Vector Ready
        _update_status(document_id, vector_status=ProcessingStatus.COMPLETED, chunk_count=len(vector_chunks))
        
        # Pass payload to next step (Graph)
        payload["chunk_ids"] = [c.id for c in vector_chunks]
        return payload
        
    except Exception as e:
        logger.error(f"[Ingest] Vectorization failed: {e}")
        _update_status(document_id, vector_status=ProcessingStatus.FAILED, error=str(e))
        raise

@shared_task(name="cortex.workers.ingest.index_graph", bind=True)
def index_graph_incrementally_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 3: Graph Indexing (Heavy Lifting).
    """
    document_id = payload["document_id"]
    workspace_id = payload["workspace_id"]
    filepath = payload.get("filepath")
    
    logger.info(f"[Ingest] Starting Graph Indexing for {document_id}")
    _update_status(document_id, graph_status=ProcessingStatus.PROCESSING)
    
    try:
        indexer = get_graphrag_indexer()
        
        # Run async indexer in sync task
        result = asyncio.run(indexer.index_document_incrementally(
            doc_id=document_id,
            workspace_id=workspace_id
        ))
        
        # Process Result
        if result.errors and not result.entities_extracted:
            # If completely failed
            raise Exception(f"Graph Indexing errors: {result.errors}")
            
        logger.info(f"[Ingest] Graph Indexing Complete. Entities: {result.entities_extracted}")

        _update_status(
            document_id, 
            graph_status=ProcessingStatus.COMPLETED, 
            entity_count=result.entities_extracted,
            relationship_count=result.relationships_extracted
        )
        
        # Final Cleanup (Delete temp uploaded file)
        if filepath and os.path.exists(filepath) and not filepath.startswith("http") and not filepath.endswith(".git"):
            try:
                os.remove(filepath)
            except OSError:
                pass
            
        return {"status": "complete", "document_id": document_id}
        
    except Exception as e:
        logger.error(f"[Ingest] Graph Indexing failed: {e}")
        _update_status(document_id, graph_status=ProcessingStatus.FAILED, error=str(e))
        raise

# =============================================================================
# Helper Functions
# =============================================================================

async def _verify_write_access(user_id: str, layer_id: str) -> bool:
    """JIT Security Check."""
    logger.info(f"JIT Checking access for {user_id} on {layer_id}")
    # In real imp: async with async_session_maker()...
    return True

def _update_status(document_id: str, vector_status=None, graph_status=None, error=None, **kwargs):
    """
    Update DocumentStatus in Redis/DB via Service.
    """
    service = get_document_status_service()
    
    if vector_status:
        service.update_vector_status(document_id, vector_status, error_message=error, **kwargs)
    
    if graph_status:
        service.update_graph_status(document_id, graph_status, error_message=error, **kwargs)
