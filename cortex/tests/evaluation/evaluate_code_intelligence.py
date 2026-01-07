
import asyncio
import json
import logging
import os
import sys
from typing import List, Dict, Any

# Add cortex to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.services.embedding import get_embedding_service
from app.services.vector_store import get_vector_store
from app.services.graphrag.neo4j_store import get_graph_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eval")

DATASET_PATH = "tests/data/code_golden_dataset.json"
WORKSPACE_ID = "default" # Assuming code is indexed here for test

async def evaluate_code_intelligence():
    """
    Evaluate retrieval recall for code queries.
    """
    logger.info("🚀 Starting Code Brain Evaluation")
    
    # 1. Load Dataset
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found at {DATASET_PATH}")
        return
        
    with open(DATASET_PATH, "r") as f:
        dataset = json.load(f)
        
    logger.info(f"Loaded {len(dataset)} test cases")
    
    # 2. Initialize Services
    embedder = get_embedding_service()
    vector_store = get_vector_store()
    graph_store = get_graph_store()
    
    results = []
    
    # 3. Run Evaluation
    total_recall = 0
    k = 5
    
    for case in dataset:
        query = case["query"]
        expected_files = set(case["expected_files"])
        expected_entities = set(case["expected_entities"])
        
        logger.info(f"\nQuery: {query}")
        
        # A. Vector Search
        embedding_result = await embedder.embed_text(query)
        embedding = embedding_result.embedding
        vector_results = vector_store.search(
            query_embedding=embedding,
            workspace_id=WORKSPACE_ID,
            top_k=k
        )
        
        # B. Graph Search (Simple keyword extraction for now)
        # In real app, we use an LLM extractor. Here we simplistic splitting for speed/test.
        keywords = query.replace("?", "").split()
        graph_results = graph_store.local_search(
            query_entities=keywords, # Very naive, real system is better
            workspace_id=WORKSPACE_ID,
            limit=k
        )
        
        # C. Combine & Check
        retrieved_files = set()
        retrieved_entities = set()
        
        # Process Vector Hits
        for res in vector_results:
            # path is usually in metadata
            meta = res.chunk.metadata or {}
            path = meta.get("file_path", "") or res.chunk.document_id # fallback
            retrieved_files.add(path)
            # Entity name might be in content or metadata
            retrieved_entities.add(meta.get("node_name", ""))
            
        # Process Graph Hits
        for entity in graph_results.get("entities", []):
             # Source docs usually stored as list
             for doc in entity.source_documents:
                 retrieved_files.add(doc)
             retrieved_entities.add(entity.name)
             
        # Check Matches (Partial match on file path)
        hit = False
        matched_file = None
        
        for exp in expected_files:
            for ret in retrieved_files:
                if exp in ret: # substring match (e.g. app/services/... in /abs/path/to/app/services...)
                    hit = True
                    matched_file = ret
                    break
            if hit: break
            
        # Check Entity Matches if file match failed (fallback)
        if not hit:
            for exp in expected_entities:
                if exp in retrieved_entities:
                    hit = True
                    break
        
        score = 1.0 if hit else 0.0
        total_recall += score
        
        logger.info(f"Hit: {hit} | Expected: {expected_files} | Matched: {matched_file}")
        
        results.append({
            "id": case["id"],
            "query": query,
            "hit": hit,
            "retrieved_files": list(retrieved_files)[:3] # sample
        })
        
    # 4. Report
    avg_recall = total_recall / len(dataset)
    logger.info(f"\n========================================")
    logger.info(f"📊 Evaluation Complete")
    logger.info(f"Recall@{k}: {avg_recall:.2%}")
    logger.info(f"========================================")
    
    # Write report
    with open("tests/evaluation/report.md", "w") as f:
        f.write(f"# Code Brain Evaluation Report\n\n")
        f.write(f"**Recall@{k}**: {avg_recall:.2%}\n\n")
        f.write("| ID | Query | Hit | Top Retrieved |\n")
        f.write("|---|---|---|---|\n")
        for r in results:
            files = ", ".join([os.path.basename(f) for f in r["retrieved_files"]])
            f.write(f"| {r['id']} | {r['query']} | {'✅' if r['hit'] else '❌'} | {files} |\n")

if __name__ == "__main__":
    asyncio.run(evaluate_code_intelligence())
