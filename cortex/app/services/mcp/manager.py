
import logging
import yaml
import os
from typing import Dict, List, Any, Optional

from app.services.mcp.client import get_mcp_client
from app.services.agent.mcp_converter import convert_all_tools

logger = logging.getLogger(__name__)

AGENTS_CONFIG_PATH = os.getenv("AGENTS_CONFIG_PATH", "/app/config/agents.yaml")

class MCPManager:
    """
    High-level manager for MCP Tools.
    Loads configuration, performs discovery, and aggregates tools.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance.client = get_mcp_client()
            cls._instance._config = cls._load_config()
            cls._instance._tool_registry = {} # { "tool_name": { "server": "git", "url": "...", "schema": ... } }
        return cls._instance

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        """Load configuration from mcp_config.json or agents.yaml (fallback)."""
        import json
        
        # 1. Rule-Compliant JSON Config
        json_path = os.getenv("MCP_CONFIG_PATH", "cortex/mcp_config.json")
        if os.path.exists(json_path):
             with open(json_path, "r") as f:
                logger.info(f"Loading MCP config from {json_path}")
                return json.load(f)
        
        # 2. Legacy YAML Config (Fallback)
        if not os.path.exists(AGENTS_CONFIG_PATH):
            # Fallback or empty if not found
            # In local dev it might be in cortex/config/agents.yaml relative to run dir
            local_path = "cortex/config/agents.yaml"
            if os.path.exists(local_path):
                 with open(local_path, "r") as f:
                    return yaml.safe_load(f)
            
            logger.warning(f"Agents config not found at {AGENTS_CONFIG_PATH} or mcp_config.json")
            return {"tools": {}, "personas": {}}
            
        with open(AGENTS_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)

    async def discover_tools(self):
        """
        Query all configured servers and populate the tool registry.
        This should be called on startup or periodically.
        """
        tools_config = self._config.get("tools", {})
        
        for server_name, server_conf in tools_config.items():
            url = server_conf.get("url")
            if not url:
                continue
                
            logger.info(f"Discovering tools from {server_name} at {url}...")
            
            # Fetch tools via Client
            tools = await self.client.list_tools(server_name, url)
            
            # Register them
            for tool in tools:
                # We assume tool names are unique globalwide OR we namespace them
                # For now, let's namespace them if collision risk, or just store metadata
                # The rule said "git_*" matching, so likely tools are named "git_commit" etc.
                
                # Check formatting of tool object (it's Pydantic model from mcp SDK)
                t_name = tool.name
                
                self._tool_registry[t_name] = {
                    "server": server_name,
                    "url": url,
                    "tool_obj": tool
                }
        
        logger.info(f"Discovery complete. Registered {len(self._tool_registry)} tools.")

    def get_tools_for_persona(self, persona_name: str) -> List[Any]:
        """
        Return the OpenAI-compatible tool definitions for a given persona.
        """
        personas = self._config.get("personas", {})
        persona_def = personas.get(persona_name)
        
        if not persona_def:
            # Default to all tools or specific fail-safe?
            # Creating a "general" persona logic might be good.
            return []
            
        allowed_patterns = persona_def.get("tools", [])
        
        # Filter registry
        selected_tools = []
        import re
        
        for name, meta in self._tool_registry.items():
            # Check matches
            for pattern in allowed_patterns:
                # Convert glob to regex: "git_*" -> "^git_.*"
                regex_pat = pattern.replace("*", ".*")
                if re.match(f"^{regex_pat}$", name):
                    selected_tools.append(meta["tool_obj"])
                    break
        
        # Convert to OpenAI format
        return convert_all_tools(selected_tools)

    def get_server_for_tool(self, tool_name: str) -> Optional[Dict[str, str]]:
        """
        Return {server_name, url} for a given tool name.
        """
        meta = self._tool_registry.get(tool_name)
        if meta:
            return {"name": meta["server"], "url": meta["url"]}
        return None

def get_mcp_manager() -> MCPManager:
    return MCPManager()
