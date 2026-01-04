
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default config path relative to the app root or defined by env
MCP_CONFIG_PATH = os.getenv("MCP_CONFIG_PATH", "/app/mcp_config.json")

def load_mcp_config() -> Dict[str, Any]:
    """
    Load MCP server configurations from JSON file.
    Returns a dictionary of server definitions.
    """
    if not os.path.exists(MCP_CONFIG_PATH):
        logger.warning(f"MCP config file not found at {MCP_CONFIG_PATH}. returning empty config.")
        return {"mcpServers": {}}

    try:
        with open(MCP_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP config: {e}")
        return {"mcpServers": {}}
    except Exception as e:
        logger.error(f"Error loading MCP config: {e}")
        return {"mcpServers": {}}

def get_mcp_server_config(server_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific MCP server."""
    config = load_mcp_config()
    return config.get("mcpServers", {}).get(server_name)
