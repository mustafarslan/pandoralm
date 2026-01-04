"""
Ingestion Worker.
Handles background processing of documents and git repositories.
"""
import os
import shutil
import git
import uuid
import logging
from typing import Optional, List
from pathlib import Path

from app.core.config import settings
from app.core.telemetry import trace_span
from app.services.vector_store import get_vector_store
from app.services.code.parser import get_code_parser
from app.services.code.graph_mapper import get_code_graph_mapper

logger = logging.getLogger(__name__)

# K8s Safety: Use mounted volume if defined, else fallback to /tmp (local dev)
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/pandora_ingest")

def process_git_repo(
    repo_url: str,
    workspace_id: str,
    layer_id: str,
    user_id: str,
    access_token: Optional[str] = None
):
    """
    Clones a Git repo, parses it, and indexes code chunks.
    """
    logger.info(f"Starting Git Ingestion for {repo_url} in workspace {workspace_id}")
    
    # 1. Setup Temp Path
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    clone_path = os.path.join(TEMP_DIR, f"{repo_name}_{uuid.uuid4()}")
    
    # 2. Add Auth to URL if needed
    auth_url = repo_url
    if access_token:
        # Simplified auth insertion (https://token@github.com/...)
        if "https://" in repo_url:
             auth_url = repo_url.replace("https://", f"https://{access_token}@")
    
    try:
        # 3. Clone
        os.makedirs(TEMP_DIR, exist_ok=True)
        logger.info(f"Cloning to {clone_path}...")
        git.Repo.clone_from(auth_url, clone_path, depth=1)
        
        # 4. Walk & Parse
        parser = get_code_parser()
        vector_store = get_vector_store()
        graph_mapper = get_code_graph_mapper()
        
        all_chunks = []
        
        for root, _, files in os.walk(clone_path):
            if ".git" in root or "node_modules" in root or "venv" in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, clone_path)
                
                # Filter by extension logic is in Parser (parse_file returns [] if unsupported)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    # Generate a pseudo-doc ID for the file
                    doc_id = f"git::{repo_name}::{rel_path}"
                    
                    chunks = parser.parse_file(
                        content=content,
                        filename=rel_path,
                        workspace_id=workspace_id,
                        layer_id=layer_id,
                        document_id=doc_id
                    )
                    
                    if chunks:
                        all_chunks.extend(chunks)
                        
                except Exception as e:
                    logger.warning(f"Failed to process file {rel_path}: {e}")
        
        # 5. Indexing (Batch)
        if all_chunks:
            logger.info(f"Indexing {len(all_chunks)} code chunks...")
            # Vector Store
            vector_store.add_chunks(all_chunks, workspace_id)
            
            # Graph Store
            graph_mapper.map_repo(all_chunks, workspace_id)
            
        logger.info(f"Successfully processed repo: {repo_url}")
        
    except Exception as e:
        logger.error(f"Git Ingestion Failed: {e}")
        raise e
    finally:
        # 6. Cleanup (Critical for K8s)
        if os.path.exists(clone_path):
            logger.info(f"Cleaning up {clone_path}...")
            shutil.rmtree(clone_path)
