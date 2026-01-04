
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.mcp_client import MCPClientService
from app.services.agent.agent import ResearchAgent

# Mock Tool
class MockTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

@pytest.fixture
def mock_mcp_config():
    with patch("app.services.mcp_client.load_mcp_config") as mock:
        mock.return_value = {
            "mcpServers": {
                "test-server": {
                    "command": "echo",
                    "args": []
                }
            }
        }
        yield mock

@pytest.mark.asyncio
async def test_mcp_client_list_tools(mock_mcp_config):
    # Mock stdio_client
    with patch("app.services.mcp_client.stdio_client") as mock_stdio:
        # Mock context manager
        mock_ctx = AsyncMock()
        mock_stdio.return_value = mock_ctx
        mock_read, mock_write = AsyncMock(), AsyncMock()
        mock_ctx.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock ClientSession
        with patch("app.services.mcp_client.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__.return_value = mock_session
            
            # Setup tool response
            mock_session.list_tools.return_value.tools = [
                MockTool("dummy_tool", "desc", {"type": "object"})
            ]
            
            client = MCPClientService()
            tools = await client.list_tools("test-server")
            
            assert len(tools) == 1
            assert tools[0].name == "dummy_tool"

@pytest.mark.asyncio
async def test_research_agent_flow():
    # Mock MCP Client
    with patch("app.services.agent.agent.get_mcp_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Return empty tools to simplify test (Agent should just speak)
        mock_client.get_all_tools.return_value = {}
        
        # Mock OpenAI Client
        with patch("app.services.agent.agent.AsyncOpenAI") as mock_openai:
            mock_ai = AsyncMock()
            mock_openai.return_value = mock_ai
            
            # Mock Response
            mock_choice = MagicMock()
            mock_choice.message.content = "Research Complete"
            mock_choice.message.tool_calls = None
            mock_ai.chat.completions.create.return_value.choices = [mock_choice]
            
            agent = ResearchAgent()
            result = await agent.execute("Test query")
            
            assert result == "Research Complete"
            mock_client.get_all_tools.assert_called_once()
