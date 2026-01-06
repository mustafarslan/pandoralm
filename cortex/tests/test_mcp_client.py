
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.mcp.client import MCPClientService
from app.services.agent.agent import ResearchAgent

# Mock Tool
class MockTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

@pytest.fixture
def mock_mcp_config():
    with patch("app.services.mcp_config.load_mcp_config") as mock:
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
    with patch("app.services.mcp.client.sse_client") as mock_stdio: # WARNING: sse_client is used in client.py
        # Wait, the code uses sse_client imported from mcp.client.sse
        # The import in client.py is: from mcp.client.sse import sse_client
        # So we should patch app.services.mcp.client.sse_client
        
        # Mock context manager
        mock_ctx = AsyncMock()
        mock_stdio.return_value = mock_ctx
        mock_read, mock_write = AsyncMock(), AsyncMock()
        mock_ctx.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock ClientSession
        with patch("app.services.mcp.client.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__.return_value = mock_session
            
            # Setup tool response
            mock_session.list_tools.return_value.tools = [
                MockTool("dummy_tool", "desc", {"type": "object"})
            ]
            
            client = MCPClientService()
            tools = await client.list_tools("test-server", "http://test-server")
            
            assert len(tools) == 1
            assert tools[0].name == "dummy_tool"

@pytest.mark.asyncio
async def test_research_agent_flow():
    # Mock MCP Client
    with patch("app.services.agent.agent.get_mcp_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Return empty tools map to simplify test (Agent should just speak)
        # get_all_tools returns Dict[str, List[Tool]]
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
            
            # Consume the stream
            events = []
            async for event in agent.execute_stream("Test query"):
                events.append(event)
            
            # Check if we got the final answer token
            final_token_event = next((e for e in events if e.event.value == "token"), None)
            assert final_token_event is not None
            assert final_token_event.data["text"] == "Research Complete"
            
            mock_client.get_all_tools.assert_called_once()
