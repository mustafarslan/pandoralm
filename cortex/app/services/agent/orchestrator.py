
import logging
import asyncio
from typing import Dict, Any, List, Optional
import json

from app.services.mcp.manager import get_mcp_manager
from app.services.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Orchestrates the execution of Agentic tasks.
    1. Determines Persona (Developer, Researcher, PM, etc.)
    2. Loads appropriate Tools
    3. Executes "Thought -> Action -> Observation" Loop (via LLM)
    """

    def __init__(self):
        self.manager = get_mcp_manager()
        self.client = get_mcp_client()

    async def determine_persona(self, query: str) -> str:
        """
        Selects the best persona for the query.
        Currently uses simple keyword matching or metadata.
        Future: Use LLM Router.
        """
        # Simple heuristic for MVP
        query = query.lower()
        if any(x in query for x in ["git", "commit", "repo", "code", "bug", "fix", "deploy"]):
            return "developer"
        if any(x in query for x in ["research", "search", "find", "news", "google"]):
            return "researcher"
        if any(x in query for x in ["plan", "ticket", "jira", "linear", "spec", "product"]):
            return "product_manager"

        # Default
        return "developer" # Or generic

    async def run_agent_loop(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent loop.

        Args:
            query: User's question
            user_context: {"user_id": ..., "layer_ids": [...]}
        """
        persona = await self.determine_persona(query)
        logger.info(f"Selected Persona: {persona} for query: {query}")

        # Get Tools
        openai_tools = self.manager.get_tools_for_persona(persona)
        if not openai_tools:
            return {"answer": "I could not find any tools for this request.", "steps": []}

        # Placeholder for full ReAct loop
        return {
            "persona": persona,
            "tools_count": len(openai_tools),
            "status": "Ready to execute with tools: " + ", ".join([t["function"]["name"] for t in openai_tools])
        }

    async def execute_tool_call(self, tool_call: Dict[str, Any], layer_ids: List[str]) -> Any:
        function = tool_call.get("function", {})
        name = function.get("name")
        arguments_json = function.get("arguments", "{}")
        try:
            arguments = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
        except:
            arguments = {}

        server_info = self.manager.get_server_for_tool(name)
        if not server_info:
            return f"Error: Tool {name} not found in registry."

        result = await self.client.call_tool(
            server_name=server_info["name"],
            server_url=server_info["url"],
            tool_name=name,
            arguments=arguments,
            layer_ids=layer_ids
        )
        return result

def get_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator()
