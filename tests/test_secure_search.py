
"""
Verification Test for Secure Hybrid Search.
Tests that documents in restricted layers are NOT returned to unauthorized users.
"""
import pytest
import shutil
import os
import lancedb
import pyarrow as pa
from unittest.mock import MagicMock, patch
from cortex.app.services.vector_store import LanceDBStore, VectorChunk

# Setup temporary test DB
TEST_DB_PATH = "./tests/data/secure_search_test/lancedb"

@pytest.fixture
def vector_store():
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)
    os.makedirs(TEST_DB_PATH, exist_ok=True)
    
    # Initialize store with local path
    with patch("cortex.app.core.config.settings.LANCEDB_PATH", TEST_DB_PATH):
        store = LanceDBStore(db_path=TEST_DB_PATH)
        yield store
        
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

def test_secure_vector_search(vector_store):
    """Verify that search filters out restricted chunks."""
    workspace_id = "ws-secure"
    
    # 1. Seed Data
    # Chunk A: Public
    chunk_public = VectorChunk(
        id="chunk_public",
        content="Public content",
        embedding=[0.1] * 1536,
        document_id="doc_1",
        workspace_id=workspace_id,
        layer_id="public",
        visibility="public"
    )
    
    # Chunk B: Restricted (HR)
    chunk_hr = VectorChunk(
        id="chunk_hr",
        content="Secret salary info",
        embedding=[0.1] * 1536, # Same embedding to match query
        document_id="doc_2",
        workspace_id=workspace_id,
        layer_id="layer_hr",
        visibility="private"
    )
    
    vector_store.add_chunks([chunk_public, chunk_hr], workspace_id)
    
    # 2. Search as Public User
    # query matches both (same embedding)
    results_public = vector_store.search(
        query_embedding=[0.1] * 1536,
        workspace_id=workspace_id,
        allowed_layers=["public", "default"]
    )
    
    assert len(results_public) == 1
    assert results_public[0].chunk.id == "chunk_public"
    print("✅ Public user only sees public chunk.")
    
    # 3. Search as HR User
    results_hr = vector_store.search(
        query_embedding=[0.1] * 1536,
        workspace_id=workspace_id,
        allowed_layers=["public", "default", "layer_hr"]
    )
    
    assert len(results_hr) == 2
    ids = [r.chunk.id for r in results_hr]
    assert "chunk_public" in ids
    assert "chunk_hr" in ids
    print("✅ HR user sees both chunks.")

def test_secure_prefiltering_enforcement(vector_store):
    """Verify prefilter=True logic via Mock."""
    # We want to verify that .where(..., prefilter=True) is called
    workspace_id = "ws-mock"
    
    # Mock the table object return from _ensure_table
    mock_table = MagicMock()
    mock_query = MagicMock()
    
    vector_store._db = MagicMock()
    vector_store._db.table_names.return_value = [f"vectors_{workspace_id}"]
    vector_store._db.open_table.return_value = mock_table
    
    mock_table.search.return_value = mock_query
    mock_query.where.return_value = mock_query # Chainable
    mock_query.limit.return_value = mock_query
    mock_query.to_list.return_value = []

    # Run Search
    vector_store.search(
        query_embedding=[0.1] * 1536,
        workspace_id=workspace_id,
        allowed_layers=["layer_a"]
    )
    
    # Verify call arguments
    # Expect: layer_id IN ('layer_a')
    # AND prefilter=True
    mock_query.where.assert_called_with("layer_id IN ('layer_a')", prefilter=True)
    print("✅ Prefilter enforcement verified.")

if __name__ == "__main__":
    # Manually run fixtures/test if executed as script to avoid invoking full pytest
    # But usually we run `pytest tests/test_secure_search.py`
    pass
