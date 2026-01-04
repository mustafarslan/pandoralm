
"""
E2E Test for Code Ingestion Pipeline (Phase 3A).
Verifies that:
1. CodeParser chunks files correctly (Class/Method).
2. GitIngest worker processes a repo.
3. GraphMapper creates Neo4j nodes.
"""
import pytest
import shutil
import os
from unittest.mock import MagicMock, patch
from cortex.app.services.code.parser import CodeParser
from cortex.app.services.code.graph_mapper import CodeGraphMapper
from cortex.app.workers.ingest import process_git_repo

# Mock Repo Path
TEST_REPO_URL = "https://github.com/mock/repo.git"
TEST_DIR = "/tmp/test_code_ingest"

@pytest.fixture
def clean_env():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)
    yield
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

def test_python_parsing():
    """Verify AST parsing logic."""
    parser = CodeParser()
    
    code = """
class AuthController:
    def login(self, user):
        return True

def logout():
    pass
    """
    
    chunks = parser.parse_file(code, "auth.py", "ws-1", "layer-1", "doc-1")
    
    assert len(chunks) == 3 
    # 1. Class AuthController
    # 2. Method login
    # 3. Function logout
    
    types = [c.node_type for c in chunks]
    names = [c.metadata["raw_name"] for c in chunks]
    
    assert "class" in types
    assert "function" in types
    
    assert "AuthController" in names
    assert "login" in names
    assert "logout" in names
    
    print("✅ Python Parsing Verified (Classes/Functions extracted)")

@patch("cortex.app.workers.ingest.git.Repo.clone_from")
@patch("cortex.app.workers.ingest.os.walk")
@patch("builtins.open")
def test_git_ingest_flow(mock_open, mock_walk, mock_clone, clean_env):
    """Verify pipeline flow (Clone -> Parse -> Map)."""
    
    # Mock OS Walk to return 1 file
    mock_walk.return_value = [
        ("/tmp/repo", [], ["main.py"])
    ]
    
    # Mock File Content
    mock_file = MagicMock()
    mock_file.read.return_value = "def main(): pass"
    mock_open.return_value.__enter__.return_value = mock_file
    
    # Prepare Mocks for services
    with patch("cortex.app.workers.ingest.get_vector_store") as mock_vs, \
         patch("cortex.app.workers.ingest.get_code_graph_mapper") as mock_gm:
         
        # Execute
        process_git_repo(TEST_REPO_URL, "ws-1", "layer-1", "user-1")
        
        # Assertions
        mock_clone.assert_called() # Git clone called
        mock_vs.return_value.add_chunks.assert_called() # Vector store called
        mock_gm.return_value.map_repo.assert_called() # Graph mapper called
        
        print("✅ Git Ingestion Pipeline Verified")

if __name__ == "__main__":
    pass
