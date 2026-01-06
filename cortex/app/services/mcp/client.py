
import logging
import asyncio
from typing import Dict, List, Any, Optional
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)

class MCPClientService:
    """
    Manages networked connections to MCP Servers via SSE.
    Maintains a pool of active sessions.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPClientService, cls).__new__(cls)
            cls._instance._sessions: Dict[str, ClientSession] = {}
            cls._instance._exit_stack = None
        return cls._instance

    async def get_session(self, server_name: str, server_url: str, layer_ids: List[str]) -> ClientSession:
        """
        Get or create a session for the given server.
        
        Args:
            server_name: Unique identifier for the tool/server
            server_url: The SSE endpoint (e.g. http://mcp-git:8080/sse)
            layer_ids: For Identity Passport (propagation of auth context)
        """
        # Note: In a real persistent system, we might cache sessions. 
        # However, for SSE, if the connection drops, we need to reconnect.
        # Also, ClientSession is context-manager based.
        
        # Identity Passport Header
        headers = {
            "X-Pandora-Layer-ID": str(layer_ids) 
        }
        
        # For simplicity in this implementation, we implement a "Connect on Demand" approach
        # that yields a temporary session, rather than a long-lived global pool that strictly persists.
        # Persistent pooling with AsyncExitStack is complex to manage globally in a singleton 
        # without robust lifecycle hooks.
        
        # We return a context manager helper/factory here is not standard pattern for "get_session"
        # Let's wrap the MCP sse_client.
        
        return sse_client(server_url, headers=headers)

    async def list_tools(self, server_name: str, server_url: str) -> List[Any]:
        """
        Connect to an MCP server (via SSE) and fetch its tools.
        """
        try:
            async with sse_client(server_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools
        except Exception as e:
            logger.error(f"Error listing tools from '{server_name}' ({server_url}): {e}")
            return []

    async def call_tool(self, server_name: str, server_url: str, tool_name: str, arguments: Dict[str, Any], layer_ids: List[str] = None) -> Any:
        """
        Execute a specific tool on an MCP server.
        """
        if layer_ids is None:
            layer_ids = []
            
        headers = {"X-Pandora-Layer-ID": str(layer_ids)}
        
        try:
            # We must pass headers to the initial HTTP request
            async with sse_client(server_url, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on '{server_name}': {e}")
            raise e

    async def get_all_tools(self) -> Dict[str, List[Any]]:
        """
        Fetch tools from all configured MCP servers.
        
        Returns:
            Dict[str, List[Tool]]: Map of server_name -> list of tools
        """
        from app.services.mcp_config import load_mcp_config
        
        config = load_mcp_config()
        tools_map = {}
        
        for name, details in config.get("tools", {}).items():
            url = details.get("url")
            if url:
                tools = await self.list_tools(name, url)
                if tools:
                    tools_map[name] = tools
        
        return tools_map

def get_mcp_client() -> MCPClientService:
    return MCPClientService()
