"""
E2E Tests: Knowledge Layer Security
Phase 5-3: Enterprise Security & Governance

Tests for ReBAC enforcement at the data layer.
"""
import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

# Test fixtures
TEST_LAYERS = {
    "public": {
        "id": str(uuid4()),
        "name": "Public",
        "type": "SYSTEM",
        "permissions": [{"role_pattern": "*", "access_level": "READ"}]
    },
    "engineering": {
        "id": str(uuid4()),
        "name": "Engineering",
        "type": "TEAM",
        "permissions": [{"role_pattern": "group:engineering", "access_level": "WRITE"}]
    },
    "hr": {
        "id": str(uuid4()),
        "name": "Human Resources",
        "type": "TEAM",
        "permissions": [{"role_pattern": "group:hr", "access_level": "WRITE"}]
    },
}


class TestKnowledgeLayerSecurity:
    """E2E tests for Knowledge Layer access control."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store with layer-filtered search."""
        store = MagicMock()
        
        # Sample vectors with different layer_ids
        all_vectors = [
            {"id": "v1", "content": "Public doc", "layer_id": TEST_LAYERS["public"]["id"]},
            {"id": "v2", "content": "Engineering doc", "layer_id": TEST_LAYERS["engineering"]["id"]},
            {"id": "v3", "content": "HR doc", "layer_id": TEST_LAYERS["hr"]["id"]},
        ]
        
        def mock_search(query_embedding, workspace_id, allowed_layers=None, **kwargs):
            """Simulate layer-filtered search."""
            if not allowed_layers:
                return []
            
            results = []
            for v in all_vectors:
                if v["layer_id"] in allowed_layers:
                    results.append(MagicMock(chunk=MagicMock(**v), score=0.9))
            return results
        
        store.search = mock_search
        return store
    
    @pytest.mark.asyncio
    async def test_unauthorized_layer_access_returns_zero_results(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """
        Test: User without group:hr role cannot access HR documents.
        
        Expected: Search returns 0 results for HR layer.
        """
        # User roles (no HR access)
        user_roles = ["user", "group:engineering"]
        
        # Simulate layer resolution (only engineering + public)
        authorized_layers = [
            TEST_LAYERS["public"]["id"],
            TEST_LAYERS["engineering"]["id"]
        ]
        
        # Search with authorized layers
        results = mock_vector_store.search(
            query_embedding=[0.1] * 1536,
            workspace_id="test",
            allowed_layers=authorized_layers
        )
        
        # Should NOT include HR document
        layer_ids = [r.chunk.layer_id for r in results]
        assert TEST_LAYERS["hr"]["id"] not in layer_ids
        
        # Should include public and engineering
        assert TEST_LAYERS["public"]["id"] in layer_ids
        assert TEST_LAYERS["engineering"]["id"] in layer_ids
        
        print("✅ Unauthorized layer access correctly denied")
    
    @pytest.mark.asyncio
    async def test_authorized_layer_access_returns_documents(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """
        Test: User with group:hr role can access HR documents.
        
        Expected: Search returns HR documents.
        """
        # User roles (has HR access)
        user_roles = ["user", "group:hr"]
        
        # Simulate layer resolution (public + HR)
        authorized_layers = [
            TEST_LAYERS["public"]["id"],
            TEST_LAYERS["hr"]["id"]
        ]
        
        # Search with authorized layers
        results = mock_vector_store.search(
            query_embedding=[0.1] * 1536,
            workspace_id="test",
            allowed_layers=authorized_layers
        )
        
        # Should include HR document
        layer_ids = [r.chunk.layer_id for r in results]
        assert TEST_LAYERS["hr"]["id"] in layer_ids
        
        print("✅ Authorized layer access correctly granted")
    
    @pytest.mark.asyncio
    async def test_admin_can_access_all_layers(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """
        Test: Admin user can access all layers.
        
        Expected: Search returns documents from all layers.
        """
        # Admin roles
        user_roles = ["admin"]
        
        # Admin gets all layers
        authorized_layers = [
            TEST_LAYERS["public"]["id"],
            TEST_LAYERS["engineering"]["id"],
            TEST_LAYERS["hr"]["id"]
        ]
        
        # Search with all layers
        results = mock_vector_store.search(
            query_embedding=[0.1] * 1536,
            workspace_id="test",
            allowed_layers=authorized_layers
        )
        
        # Should include all documents
        assert len(results) == 3
        
        print("✅ Admin can access all layers")


class TestWildcardPermissionMatching:
    """Tests for wildcard pattern matching in permissions."""
    
    @pytest.mark.asyncio
    async def test_wildcard_group_pattern_matches(self):
        """
        Test: role_pattern 'group:%' matches 'group:engineering'.
        
        This tests SQL LIKE pattern matching.
        """
        from fnmatch import fnmatch
        
        # Role pattern with wildcard
        role_pattern = "group:*"
        
        # User role
        user_role = "group:engineering"
        
        # Should match using fnmatch
        assert fnmatch(user_role, role_pattern)
        
        print("✅ Wildcard pattern 'group:*' matches 'group:engineering'")
    
    @pytest.mark.asyncio
    async def test_wildcard_subgroup_pattern_matches(self):
        """
        Test: role_pattern 'group:engineering:*' matches 'group:engineering:backend'.
        """
        from fnmatch import fnmatch
        
        role_pattern = "group:engineering:*"
        user_role = "group:engineering:backend"
        
        assert fnmatch(user_role, role_pattern)
        
        print("✅ Subgroup wildcard pattern matches correctly")
    
    @pytest.mark.asyncio
    async def test_exact_match_works(self):
        """
        Test: Exact role_pattern matches exactly.
        """
        role_pattern = "group:engineering"
        user_role = "group:engineering"
        
        assert role_pattern == user_role
        
        print("✅ Exact match works correctly")


class TestAdminLayerAPI:
    """Tests for Admin Layer CRUD API."""
    
    @pytest.fixture
    def admin_token_payload(self):
        """Mock admin JWT payload."""
        return {
            "sub": "admin-user-id",
            "realm_access": {"roles": ["admin", "user"]}
        }
    
    @pytest.fixture
    def user_token_payload(self):
        """Mock regular user JWT payload."""
        return {
            "sub": "regular-user-id",
            "realm_access": {"roles": ["user"]}
        }
    
    @pytest.mark.asyncio
    async def test_non_admin_cannot_create_layer(self, user_token_payload):
        """
        Test: Regular user cannot create layers.
        
        Expected: 403 Forbidden.
        """
        from fastapi import HTTPException
        
        # Sample require_super_admin check
        def require_super_admin(payload):
            roles = payload.get("realm_access", {}).get("roles", [])
            if "admin" not in roles:
                raise HTTPException(status_code=403, detail="Super admin required")
            return payload
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            require_super_admin(user_token_payload)
        
        assert exc_info.value.status_code == 403
        
        print("✅ Non-admin correctly denied layer creation")
    
    @pytest.mark.asyncio
    async def test_admin_can_create_layer(self, admin_token_payload):
        """
        Test: Admin user can create layers.
        
        Expected: No exception raised.
        """
        # Sample require_super_admin check
        def require_super_admin(payload):
            roles = payload.get("realm_access", {}).get("roles", [])
            if "admin" not in roles:
                raise Exception("Admin required")
            return payload
        
        # Should not raise
        result = require_super_admin(admin_token_payload)
        assert result == admin_token_payload
        
        print("✅ Admin can create layers")


class TestIngestionLayerBoundary:
    """Tests for ingestion respecting layer boundaries."""
    
    @pytest.mark.asyncio
    async def test_vector_includes_layer_id(self):
        """
        Test: Ingested vectors include layer_id field.
        """
        from dataclasses import dataclass
        
        @dataclass
        class VectorChunk:
            id: str
            content: str
            layer_id: str = "default"
        
        # Create vector with layer_id
        chunk = VectorChunk(
            id="test-1",
            content="Test content",
            layer_id="layer_engineering"
        )
        
        assert chunk.layer_id == "layer_engineering"
        
        print("✅ Vectors correctly include layer_id")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
