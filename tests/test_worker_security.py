"""
Test Worker Security
Phase 5.3: JIT (Just-In-Time) Permission Checks.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from cortex.workers.ingest import process_document_task

@pytest.fixture
def mock_layer_manager():
    # Patch the async helper
    # Since asyncio.run is used, we can patch the underlying coroutine or the result
    return AsyncMock()

def test_ingest_denies_revoked_user():
    """
    Scenario: User uploaded file, API accepted.
    But before Worker picked it up, User was removed from Team Layer.
    """
    # Patch both the verify access (Async) and other components
    with patch("cortex.workers.ingest._verify_write_access", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False
        
        result = process_document_task(
            filepath="/tmp/fake.pdf",
            document_id="doc-123",
            workspace_id="ws-1",
            layer_id="layer-engineering",
            user_id="user-revoked"
        )
        
        assert result["status"] == "failed"
        assert "Access Denied" in result["error"]

def test_ingest_allows_valid_user():
    """
    Scenario: User has valid access.
    """
    with patch("cortex.workers.ingest._verify_write_access", new_callable=AsyncMock) as mock_verify, \
         patch("os.path.exists", return_value=True), \
         patch("builtins.open", new_callable=MagicMock) as mock_file, \
         patch("cortex.workers.ingest.get_chunker") as mock_chunker, \
         patch("cortex.workers.ingest.get_embedding_service") as mock_embedder, \
         patch("cortex.workers.ingest.get_vector_store") as mock_vstore:
         
         mock_verify.return_value = True
         
         # Mock file read
         mock_file.return_value.__enter__.return_value.read.return_value = "Test content"
         
         # Mock chunking
         mock_chunk_preview = MagicMock()
         mock_chunk_preview.content = "Test content"
         mock_chunker.return_value.chunk_text.return_value = [mock_chunk_preview]
         
         # Mock Embedding
         mock_embedder.return_value.embed_query.return_value = [0.1, 0.2]
         
         # Mock Store
         mock_vstore.return_value.add_chunks.return_value = 1
         
         result = process_document_task(
             filepath="/tmp/valid.pdf",
             document_id="doc-123",
             workspace_id="ws-1",
             layer_id="layer-engineering",
             user_id="user-valid"
         )
         
         assert result["status"] == "complete"
         assert result["chunks"] == 1
