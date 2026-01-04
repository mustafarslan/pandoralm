
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.mcp.client import MCPClientService
from app.services.mcp.manager import MCPManager
from app.services.agent.orchestrator import AgentOrchestrator

# Mock the sse_client context manager
@pytest.fixture
def mock_sse_client():
    with patch("app.services.mcp.client.sse_client") as mock:
        # The context manager should yield (read, write) streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        # Configure __aenter__ to return the tuple
        mock.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        yield mock

@pytest.fixture
def mock_session():
    with patch("app.services.mcp.client.ClientSession") as mock:
        session_instance = AsyncMock()
        mock.return_value.__aenter__.return_value = session_instance
        yield session_instance

@pytest.mark.asyncio
async def test_mcp_client_list_tools(mock_sse_client, mock_session):
    """Test that list_tools calls the remote server via SSE/Session."""
    client = MCPClientService()
    
    # Setup mock return
    mock_tool = MagicMock()
    mock_tool.name = "git_commit"
    mock_tool_list = MagicMock()
    mock_tool_list.tools = [mock_tool]
    
    mock_session.list_tools.return_value = mock_tool_list
    
    tools = await client.list_tools("git_server", "http://fake-url/sse")
    
    assert len(tools) == 1
    assert tools[0].name == "git_commit"
    
    # Verify sse_client called with correct URL
    mock_sse_client.assert_called() 
    args, _ = mock_sse_client.call_args
    assert args[0] == "http://fake-url/sse"

@pytest.mark.asyncio
async def test_manager_discovery(mock_sse_client, mock_session):
    """Test that Manager discovers tools from config."""
    # Mock config loading
    with patch("app.services.mcp.manager.MCPManager._load_config") as mock_config:
        mock_config.return_value = {
            "tools": {
                "git_server": {"url": "http://git:8080/sse"}
            },
            "personas": {}
        }
        
        manager = MCPManager()
        
        # Setup mock return for list_tools
        mock_tool = MagicMock()
        mock_tool.name = "git_status"
        mock_tool_list = MagicMock()
        mock_tool_list.tools = [mock_tool]
        mock_session.list_tools.return_value = mock_tool_list

        await manager.discover_tools()
        
        assert "git_status" in manager._tool_registry
        assert manager._tool_registry["git_status"]["server"] == "git_server"

@pytest.mark.asyncio
async def test_orchestrator_flow():
    """Test Orchestrator persona selection and tool retrieval."""
    # Mock Manager to return known tools
    with patch("app.services.agent.orchestrator.get_mcp_manager") as mock_get_manager:
        manager_instance = MagicMock()
        mock_get_manager.return_value = manager_instance
        
        # Orchestrator
        orch = AgentOrchestrator()
        
        # Test Persona Selection
        persona = await orch.determine_persona("Fix the bug in main.py")
        assert persona == "developer"
        
        persona = await orch.determine_persona("Research competitor pricing")
        assert persona == "researcher"
        
        # Test Run Loop (Simulation)
        manager_instance.get_tools_for_persona.return_value = [{"function": {"name": "git_status"}}]
        
        result = await orch.run_agent_loop("Fix the bug", {})
        
        assert result["persona"] == "developer"
        assert result["tools_count"] == 1
        assert "Ready to execute" in result["status"]
