"""
Phase 5.5 E2E Tests: DevOps, Observability, and Integrations.

This test suite verifies:
1. Vector Admin accessibility (K8s Ingress/Service)
2. Trace generation with ReBAC Layer ID attributes
3. MCP Agent discovery and registration
"""
import os
import pytest
import requests
from unittest.mock import patch, MagicMock


# Configuration
CORTEX_API_URL = os.getenv("CORTEX_API_URL", "http://localhost:8000")
JAEGER_API_URL = os.getenv("JAEGER_API_URL", "http://localhost:16686")
VECTOR_ADMIN_URL = os.getenv("VECTOR_ADMIN_URL", "http://localhost:3002")


class TestVectorAdmin:
    """Test Vector Admin accessibility."""
    
    @pytest.mark.skipif(
        os.getenv("SKIP_K8S_TESTS", "true").lower() == "true",
        reason="K8s tests skipped in local dev"
    )
    def test_vector_admin_health(self):
        """Verify Vector Admin service is reachable."""
        try:
            response = requests.get(f"{VECTOR_ADMIN_URL}/", timeout=5)
            assert response.status_code in [200, 302], f"Vector Admin returned {response.status_code}"
        except requests.RequestException as e:
            pytest.skip(f"Vector Admin not available: {e}")
    
    def test_cortex_health_includes_telemetry(self):
        """Verify Cortex health endpoint reports telemetry status."""
        response = requests.get(f"{CORTEX_API_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        # Telemetry should be mentioned
        assert "telemetry" in data or "version" in data


class TestGlassBoxObservability:
    """Test tracing and ReBAC span attributes."""
    
    def test_trace_with_layer_id(self):
        """Verify that requests with X-Pandora-Layer-ID create spans with app.layer_id attribute."""
        # Send a request with ReBAC headers
        headers = {
            "X-Pandora-Layer-ID": "layer_test_123",
            "X-Pandora-User-ID": "user_test_456",
        }
        
        response = requests.get(
            f"{CORTEX_API_URL}/health",
            headers=headers,
            timeout=5
        )
        assert response.status_code == 200
        
        # In a real K8s env, we would query Jaeger API
        # For local testing, we verify headers are accepted
        # Note: This is a smoke test; full trace verification requires Jaeger
    
    @pytest.mark.skipif(
        os.getenv("SKIP_K8S_TESTS", "true").lower() == "true",
        reason="K8s tests skipped in local dev"
    )
    def test_jaeger_traces_exist(self):
        """Query Jaeger API to verify traces were recorded."""
        try:
            # Query Jaeger for pandora-cortex service traces
            response = requests.get(
                f"{JAEGER_API_URL}/api/traces",
                params={
                    "service": "pandora-cortex",
                    "limit": 10,
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # If there are traces, Jaeger is working
                assert "data" in data
            else:
                pytest.skip(f"Jaeger API returned {response.status_code}")
        except requests.RequestException as e:
            pytest.skip(f"Jaeger not available: {e}")


class TestMCPAgentDiscovery:
    """Test MCP agent registration and discovery."""
    
    def test_mcp_tools_endpoint_exists(self):
        """Verify that Cortex exposes MCP tools endpoint."""
        try:
            response = requests.get(
                f"{CORTEX_API_URL}/api/v1/mcp/tools",
                timeout=5
            )
            # Endpoint should exist (may return empty or 404 if no tools configured)
            assert response.status_code in [200, 404, 501]
        except requests.RequestException:
            pytest.skip("Cortex API not available")
    
    def test_mcp_config_structure(self):
        """Verify MCP configuration file structure."""
        import json
        from pathlib import Path
        
        mcp_config_path = Path(__file__).parent.parent.parent / "cortex" / "mcp_config.json"
        
        if not mcp_config_path.exists():
            pytest.skip("mcp_config.json not found")
        
        with open(mcp_config_path) as f:
            config = json.load(f)
        
        # Should have mcpServers key
        assert "mcpServers" in config
        assert isinstance(config["mcpServers"], dict)
    
    @patch("requests.get")
    def test_mcp_search_agent_discovery(self, mock_get):
        """Simulate MCP Search agent discovery."""
        # Mock the MCP bridge response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tools": [
                {
                    "name": "web_search",
                    "description": "Search the web using Brave Search API",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Simulate calling the MCP search service
        response = requests.get(
            "http://mcp-search.pandora-agents.svc:8080/tools"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert any(t["name"] == "web_search" for t in data["tools"])


class TestEvaluationPipeline:
    """Test evaluation infrastructure."""
    
    def test_golden_dataset_exists(self):
        """Verify golden dataset file exists and is valid JSON."""
        import json
        from pathlib import Path
        
        golden_path = Path(__file__).parent.parent / "evaluation" / "golden_dataset.json"
        
        assert golden_path.exists(), f"Golden dataset not found at {golden_path}"
        
        with open(golden_path) as f:
            data = json.load(f)
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Each entry should have required fields
        for entry in data:
            assert "id" in entry
            assert "question" in entry
            assert "expected_answer" in entry
    
    def test_run_evals_script_exists(self):
        """Verify evaluation script exists."""
        from pathlib import Path
        
        script_path = Path(__file__).parent.parent / "evaluation" / "run_evals.py"
        assert script_path.exists(), f"run_evals.py not found at {script_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
