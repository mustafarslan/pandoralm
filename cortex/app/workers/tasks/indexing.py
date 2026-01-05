"""
Celery Indexing Tasks
Background jobs for document processing and GraphRAG indexing

Two-Tier Architecture:
- Fast Lane: vectorize_document (seconds) → VECTOR_READY
- Heavy Lifting: start_graph_indexing (minutes/hours) → GRAPH_READY
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from celery import shared_task, chain, chord, group

from app.workers.celery_app import celery_app

from app.workers.ingest import process_git_repo # Import the sync function
from app.models.document_status import ProcessingStatus

@celery_app.task
def ingest_git_repo_task(repo_url: str, workspace_id: str, layer_id: str, user_id: str, access_token: Optional[str] = None):
    """
    Async wrapper for Git Ingestion.
    """
    process_git_repo(repo_url, workspace_id, layer_id, user_id, access_token)

logger = logging.getLogger(__name__)


# =============================================================================
# Fast Lane Task: Vectorization (seconds)
# =============================================================================

@celery_app.task(bind=True, name="indexing.vectorize_document")
def vectorize_document(
    self,
    document_id: str,
    workspace_id: str,
    filename: str,
    file_path: str,
    layer_id: str = "default",  # New
    user_id: Optional[str] = None, # New for JIT
    trigger_graph_indexing: bool = True,
) -> Dict[str, Any]:
    """
    Fast Lane: Vectorize document for immediate search availability.
    
    This task:
    1. Extracts text from document
    2. Chunks the text
    3. Generates embeddings
    4. Stores in LanceDB
    5. Updates status to VECTOR_COMPLETED
    6. Optionally chains to GraphRAG indexing
    
    Args:
        document_id: Unique document identifier
        workspace_id: Workspace the document belongs to
        filename: Original filename
        file_path: Path to the document file
        trigger_graph_indexing: Whether to chain to graph indexing (default: True)
    
    Returns:
        Dict with vectorization results
    """
    from app.services.document_status_service import get_document_status_service
    from app.services import get_vector_store, get_embedding_service
    from app.services.chunking import chunk_text
    from app.services.document_processor.extract_text import extract_text
    
    status_service = get_document_status_service()
    
    # ---------------------------------------------------------
    # JIT Security Check (Time-of-Check Time-of-Use protection)
    # ---------------------------------------------------------
    if user_id and layer_id != "default":
        # TODO: Replace with real RBAC service call
        # e.g. rbac_service.check_write_permission(user_id, layer_id)
        logger.info(f"🔒 Performing JIT Access Check for User {user_id} on Layer {layer_id}")
        
        # Simulating check (Pass for now, or fail if user_id is 'blocked')
        if user_id == "blocked_user":
             logger.error(f"⛔ JIT Access Denied for User {user_id}")
             status_service.update_vector_status(
                document_id=document_id,
                status=ProcessingStatus.FAILED,
                error_message="Access Denied (JIT Check Failed)",
            )
             return {"status": "failed", "reason": "access_denied"}
    # ---------------------------------------------------------
    
    try:
        # Update status to processing
        status_service.update_vector_status(
            document_id=document_id,
            status=ProcessingStatus.PROCESSING,
            progress=0.1,
            task_id=self.request.id,
        )
        
        logger.info(f"Vectorizing document: {document_id} ({filename})")
        
        # Step 1: Extract text (10%)
        self.update_state(state='PROGRESS', meta={
            'phase': 'extracting_text',
            'progress': 0.1,
        })
        
        import os
        directory = os.path.dirname(file_path)
        basename = os.path.basename(file_path)
        
        success, reason, metadata = extract_text(directory, basename)
        if not success:
            raise Exception(f"Text extraction failed: {reason}")
        
        # Get extracted text content
        # Legacy parsers return a list of metadata dicts
        if isinstance(metadata, list):
            if not metadata:
                 raise Exception("No metadata returned from extraction")
            metadata = metadata[0]
            
        text_content = metadata.get("pageContent", "")
        if not text_content:
            text_content = metadata.get("content", "") # Fallback
            
        if not text_content:
            raise Exception("No text content extracted from document")
        
        status_service.update_vector_status(document_id, ProcessingStatus.PROCESSING, 0.2)
        
        # Initialize Event Loop for Async Operations (Chunking -> Embedding -> Storing)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # ---------------------------------------------------------
        # Federated Layer Routing Logic
        # ---------------------------------------------------------
        target_workspace_id = workspace_id
        if layer_id and layer_id != "default":
            async def check_layer_global():
                try:
                    from app.core.database import async_session_maker as async_session_factory
                    from app.models.layer import Layer
                    async with async_session_factory() as session:
                         layer = await session.get(Layer, layer_id)
                         return layer.is_global if layer else False
                except Exception as e:
                    logger.warning(f"Failed to check global layer status: {e}")
                    return False

            if loop.run_until_complete(check_layer_global()):
                target_workspace_id = "global"
                logger.info(f"Routing document {document_id} to GLOBAL vector store (Layer {layer_id})")
        
        try:
            # Step 2: Chunk text (30%) - Parallel/Process Pool
            self.update_state(state='PROGRESS', meta={
                'phase': 'chunking',
                'progress': 0.3,
            })
            
            # Import parallel chunker
            from app.services.chunking import chunk_text_parallel
            
            # Run chunking in process pool via async wrapper
            chunks = loop.run_until_complete(
                chunk_text_parallel(
                    text=text_content,
                    chunk_size=512,
                    chunk_overlap=50,
                )
            )
            
            logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            status_service.update_vector_status(document_id, ProcessingStatus.PROCESSING, 0.4)
            
            # Step 3: Generate embeddings (70%)
            self.update_state(state='PROGRESS', meta={
                'phase': 'embedding',
                'progress': 0.5,
            })
            
            embedding_service = get_embedding_service()
            vector_store = get_vector_store()
            
            # =====================================================================
            # HIGH-PERFORMANCE PARALLEL EMBEDDING
            # =====================================================================
            
            async def embed_all_chunks():
                """Embed all chunks in parallel batches."""
                texts = [chunk["content"] for chunk in chunks]
                
                # Use the new parallel embedding service
                results = await embedding_service.embed_texts(texts)
                
                # Build embedded chunks with results
                embedded = []
                for i, (chunk, result) in enumerate(zip(chunks, results)):
                    embedded.append({
                        "id": f"{document_id}_chunk_{i}",
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "layer_id": layer_id,
                        "content": chunk["content"],
                        "embedding": result.embedding,
                        "metadata": chunk.get("metadata", {}),
                    })
                return embedded
            
            # Status update: embedding started
            status_service.update_vector_status(
                document_id, ProcessingStatus.PROCESSING, 0.5
            )
            
            # Execute parallel embedding
            embedded_chunks = loop.run_until_complete(embed_all_chunks())
            
            logger.info(f"[Parallel] Embedded {len(embedded_chunks)} chunks for {document_id}")
            
            # Step 4: Store in LanceDB (90%) - single bulk insert
            self.update_state(state='PROGRESS', meta={
                'phase': 'storing',
                'progress': 0.9,
            })
            
            status_service.update_vector_status(
                document_id, ProcessingStatus.PROCESSING, 0.9
            )
            
            loop.run_until_complete(
                vector_store.add_chunks_batch(embedded_chunks, target_workspace_id)
            )
            
        finally:
            loop.close()
        
        # Step 5: Mark as completed (100%)
        status_service.update_vector_status(
            document_id=document_id,
            status=ProcessingStatus.COMPLETED,
            progress=1.0,
            chunk_count=len(embedded_chunks),
        )
        
        logger.info(f"Vectorization complete for {document_id}: {len(embedded_chunks)} chunks")
        
        # Step 6: Chain to GraphRAG indexing if enabled
        if trigger_graph_indexing:
            logger.info(f"Chaining to GraphRAG indexing for {document_id} (rate limited: 5/m)")
            
            # Update graph status to QUEUED (waiting in rate-limited queue)
            status_service.update_graph_status(
                document_id=document_id,
                status=ProcessingStatus.QUEUED,
            )
            
            # Queue rate-limited graph indexing task
            # This prevents burning 10,000 tokens/sec on bulk uploads
            trigger_graph_indexing_task.delay(
                document_id=document_id,
                workspace_id=workspace_id,
                layer_id=layer_id,
                chunk_count=len(embedded_chunks),
            )
        
        return {
            "status": "completed",
            "document_id": document_id,
            "workspace_id": workspace_id,
            "chunks_created": len(embedded_chunks),
            "graph_indexing_triggered": trigger_graph_indexing,
        }
        
    except Exception as e:
        logger.error(f"Vectorization failed for {document_id}: {e}")
        
        status_service.update_vector_status(
            document_id=document_id,
            status=ProcessingStatus.FAILED,
            error_message=str(e),
        )
        
        raise


# =============================================================================
# Rate-Limited Graph Indexing Trigger (prevents token burn on bulk uploads)
# =============================================================================

@celery_app.task(
    bind=True,
    name="indexing.trigger_graph_indexing",
    rate_limit="5/m",  # Max 5 graph indexing tasks per minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def trigger_graph_indexing_task(
    self,
    document_id: str,
    workspace_id: str,
    layer_id: str = "default",
    chunk_count: int = 0,
) -> Dict[str, Any]:
    """
    Rate-limited trigger for incremental GraphRAG indexing.
    
    Called automatically after vectorization via Celery chain.
    Rate limited to 5 invocations per minute to prevent LLM token burn
    when users upload folders of PDFs.
    
    This task:
    1. Updates status to PROCESSING
    2. Calls incremental graph indexer (extracts from LanceDB, not PDF)
    3. Marks affected communities as stale (Redis SADD)
    4. Updates status to COMPLETED
    
    Args:
        document_id: Document to index
        workspace_id: Workspace the document belongs to
        layer_id: Target Knowledge Layer ID
        chunk_count: Number of chunks (for logging)
    
    Returns:
        Dict with indexing results
    """
    from app.services.document_status_service import get_document_status_service
    from app.services.graphrag import get_graphrag_indexer
    from app.services.graphrag.stale_community_tracker import get_stale_community_tracker
    
    status_service = get_document_status_service()
    
    logger.info(
        f"[Rate Limited] Starting incremental graph indexing for {document_id} "
        f"(workspace: {workspace_id}, layer: {layer_id}, chunks: {chunk_count})"
    )
    
    try:
        # Update status to PROCESSING
        status_service.update_graph_status(
            document_id=document_id,
            status=ProcessingStatus.PROCESSING,
            progress=0.1,
            task_id=self.request.id,
        )
        
        # Get the indexer
        indexer = get_graphrag_indexer()
        stale_tracker = get_stale_community_tracker()
        
        # Run incremental indexing (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def progress_callback(phase: str, progress: float, message: str):
            self.update_state(state='PROGRESS', meta={
                'progress': progress,
                'phase': phase,
                'message': message,
            })
            # Update database progress
            status_service.update_graph_status(
                document_id=document_id,
                status=ProcessingStatus.PROCESSING,
                progress=progress,
            )
        
        try:
            result = loop.run_until_complete(
                indexer.index_document_incrementally(
                    doc_id=document_id,
                    workspace_id=workspace_id,
                    layer_id=layer_id,
                    progress_callback=progress_callback,
                )
            )
        finally:
            loop.close()
        
        # Mark affected communities as stale (for nightly summarization)
        if result.affected_community_ids:
            stale_tracker.mark_stale(
                community_ids=result.affected_community_ids,
                workspace_id=workspace_id,
            )
            logger.info(
                f"Marked {len(result.affected_community_ids)} communities as stale "
                f"for {document_id}"
            )
        
        # Update status to COMPLETED
        status_service.update_graph_status(
            document_id=document_id,
            status=ProcessingStatus.COMPLETED,
            progress=1.0,
            entity_count=result.entities_extracted,
            relationship_count=result.relationships_extracted,
        )
        
        logger.info(
            f"Incremental graph indexing complete for {document_id}: "
            f"{result.entities_extracted} entities, {result.relationships_extracted} relationships"
        )
        
        return {
            "status": "completed",
            "document_id": document_id,
            "workspace_id": workspace_id,
            "entities_extracted": result.entities_extracted,
            "relationships_extracted": result.relationships_extracted,
            "communities_affected": len(result.affected_community_ids) if result.affected_community_ids else 0,
        }
        
    except Exception as e:
        logger.error(f"Graph indexing failed for {document_id}: {e}")
        
        status_service.update_graph_status(
            document_id=document_id,
            status=ProcessingStatus.FAILED,
            error_message=str(e),
        )
        
        raise


# =============================================================================
# Heavy Lifting Task: Batch GraphRAG Indexing (minutes/hours)
# =============================================================================

@celery_app.task(
    bind=True, 
    name="indexing.start_graph_indexing",
    soft_time_limit=21600,  # 6 hours soft limit for large document sets
    time_limit=25200,       # 7 hours hard limit
)
def start_graph_indexing(self, document_ids: List[str], workspace_id: str) -> Dict[str, Any]:
    """
    Start the GraphRAG indexing pipeline for documents.
    
    This task orchestrates:
    1. Fetching document chunks from LanceDB
    2. Extracting entities using LLM
    3. Extracting relationships
    4. Detecting communities
    5. Storing in Neo4j
    """
    from app.services import get_vector_store
    from app.services.graphrag import get_graphrag_indexer
    
    # Update task state
    self.update_state(state='PROGRESS', meta={
        'progress': 0.0,
        'phase': 'fetching_chunks',
        'entities_extracted': 0,
        'relationships_extracted': 0,
        'communities_detected': 0,
    })
    
    # Get chunks for documents
    vector_store = get_vector_store()
    all_chunks = []
    
    for doc_id in document_ids:
        chunks = vector_store.get_chunks(
            workspace_id=workspace_id,
            document_id=doc_id,
            limit=1000,
        )
        for chunk in chunks:
            all_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
                "document_id": chunk.document_id,
            })
    
    if not all_chunks:
        return {
            "status": "completed",
            "workspace_id": workspace_id,
            "message": "No chunks found for indexing",
            "entities_extracted": 0,
            "relationships_extracted": 0,
            "communities_detected": 0,
        }
    
    # Run async indexing pipeline
    indexer = get_graphrag_indexer()
    
    def progress_callback(phase: str, progress: float, message: str):
        self.update_state(state='PROGRESS', meta={
            'progress': progress,
            'phase': phase,
            'message': message,
            'entities_extracted': 0,
            'relationships_extracted': 0,
            'communities_detected': 0,
        })
    
    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            indexer.index_chunks(
                chunks=all_chunks,
                workspace_id=workspace_id,
                progress_callback=progress_callback,
            )
        )
    finally:
        loop.close()
    
    return {
        "status": "completed",
        "workspace_id": workspace_id,
        **result.to_dict(),
    }


@celery_app.task(bind=True, name="indexing.reindex_vectors")
def reindex_vectors(self, workspace_id: str) -> Dict[str, Any]:
    """
    Reindex all vectors for a workspace.
    
    Re-generates embeddings for all chunks.
    """
    import asyncio
    from app.services import get_vector_store, get_embedding_service
    
    self.update_state(state='PROGRESS', meta={
        'progress': 0.0,
        'phase': 'fetching_chunks',
    })
    
    vector_store = get_vector_store()
    embedding_service = get_embedding_service()
    
    # Get all chunks
    chunks = vector_store.get_chunks(workspace_id=workspace_id, limit=10000)
    
    if not chunks:
        return {"status": "completed", "reindexed": 0}
    
    total = len(chunks)
    reindexed = 0
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        for i, chunk in enumerate(chunks):
            # Regenerate embedding
            result = loop.run_until_complete(
                embedding_service.embed_text(chunk.content)
            )
            
            # Update chunk
            vector_store.update_chunk(
                chunk_id=chunk.id,
                workspace_id=workspace_id,
                content=chunk.content,
                embedding=result.embedding,
            )
            
            reindexed += 1
            
            if i % 10 == 0:
                self.update_state(state='PROGRESS', meta={
                    'progress': (i + 1) / total,
                    'phase': 'reindexing',
                    'reindexed': reindexed,
                    'total': total,
                })
    finally:
        loop.close()
    
    return {
        "status": "completed",
        "workspace_id": workspace_id,
        "reindexed": reindexed,
        "total": total,
    }


@celery_app.task(bind=True, name="indexing.extract_entities_batch")
def extract_entities_batch(
    self,
    chunks: List[Dict[str, str]],
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Extract entities from a batch of chunks.
    
    Used as part of parallel processing in chord pattern.
    """
    import asyncio
    from app.services.graphrag import get_entity_extractor
    
    extractor = get_entity_extractor()
    all_entities = []
    all_relationships = []
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        for chunk in chunks:
            chunk_id = chunk.get("id", "")
            content = chunk.get("content", "")
            
            # Extract entities
            entities = loop.run_until_complete(
                extractor.extract_entities(content, chunk_id)
            )
            all_entities.extend([e.to_dict() for e in entities])
            
            # Extract relationships
            if entities:
                relationships = loop.run_until_complete(
                    extractor.extract_relationships(content, entities, chunk_id)
                )
                all_relationships.extend([r.to_dict() for r in relationships])
    finally:
        loop.close()
    
    return {
        "workspace_id": workspace_id,
        "entities": all_entities,
        "relationships": all_relationships,
        "chunks_processed": len(chunks),
    }


@celery_app.task(name="indexing.combine_and_store")
def combine_and_store(
    results: List[Dict[str, Any]],
    workspace_id: str,
) -> Dict[str, Any]:
    """
    Combine extraction results and store in Neo4j.
    
    Callback task for chord pattern.
    """
    import uuid
    from app.services.graphrag import (
        get_graph_store,
        get_community_detector,
        Entity,
        Relationship,
    )
    
    graph_store = get_graph_store()
    detector = get_community_detector()
    
    # Combine all entities and relationships
    all_entities_data = []
    all_rels_data = []
    
    for result in results:
        all_entities_data.extend(result.get("entities", []))
        all_rels_data.extend(result.get("relationships", []))
    
    # Deduplicate entities by name
    entity_map = {}
    for e in all_entities_data:
        key = e["name"].lower()
        if key not in entity_map:
            entity_map[key] = Entity(
                id=f"ent_{uuid.uuid4().hex[:12]}",
                name=e["name"],
                type=e["type"],
                description=e["description"],
                source_documents=[e["source_chunk_id"]],
            )
    
    entities = list(entity_map.values())
    
    # Build name to entity mapping
    name_to_entity = {e.name.lower(): e for e in entities}
    
    # Convert relationships
    relationships = []
    for r in all_rels_data:
        source = name_to_entity.get(r["source_entity"].lower())
        target = name_to_entity.get(r["target_entity"].lower())
        if source and target:
            relationships.append(Relationship(
                id=f"rel_{uuid.uuid4().hex[:12]}",
                source_id=source.id,
                target_id=target.id,
                type=r["relationship_type"],
                description=r["description"],
            ))
    
    # Detect communities
    communities = detector.detect_communities(entities, relationships)
    
    # Store in Neo4j
    graph_store.create_indexes(workspace_id)
    
    if entities:
        graph_store.upsert_entities_batch(entities, workspace_id)
    
    if relationships:
        graph_store.upsert_relationships_batch(relationships, workspace_id)
    
    for comm in communities:
        graph_store.upsert_community(comm, workspace_id)
    
    return {
        "status": "completed",
        "workspace_id": workspace_id,
        "entities_stored": len(entities),
        "relationships_stored": len(relationships),
        "communities_stored": len(communities),
    }


def create_parallel_indexing_workflow(
    document_ids: List[str],
    workspace_id: str,
    batch_size: int = 10,
) -> chord:
    """
    Create a chord workflow for parallel entity extraction.
    
    Pattern:
    1. Parallel: Extract entities from chunk batches
    2. Callback: Combine results and store in Neo4j
    """
    from app.services import get_vector_store
    
    vector_store = get_vector_store()
    
    # Get all chunks
    all_chunks = []
    for doc_id in document_ids:
        chunks = vector_store.get_chunks(
            workspace_id=workspace_id,
            document_id=doc_id,
            limit=1000,
        )
        for chunk in chunks:
            all_chunks.append({
                "id": chunk.id,
                "content": chunk.content,
            })
    
    # Create batches
    batches = [
        all_chunks[i:i + batch_size]
        for i in range(0, len(all_chunks), batch_size)
    ]
    
    # Create chord: parallel extraction → combine and store
    extraction_tasks = group(
        extract_entities_batch.s(batch, workspace_id)
        for batch in batches
    )
    
    return chord(extraction_tasks)(combine_and_store.s(workspace_id))
