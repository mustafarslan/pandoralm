
from typing import Dict, Any, List
# We assume standard MCP Tool structure which uses JSON Schema for input_schema

def convert_mcp_tool_to_openai(mcp_tool: Any) -> Dict[str, Any]:
    """
    Convert an MCP Tool object to an OpenAI function definition.
    
    Args:
        mcp_tool: An object with name, description, and inputSchema (pydantic model or dict)
        
    Returns:
        Dict matching OpenAI's 'function' schema
    """
    # Handle both Pydantic model and dict
    if hasattr(mcp_tool, "name"):
        name = mcp_tool.name
        description = mcp_tool.description
        input_schema = mcp_tool.inputSchema
    else:
        name = mcp_tool.get("name")
        description = mcp_tool.get("description")
        input_schema = mcp_tool.get("inputSchema")

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description or "",
            "parameters": input_schema
        }
    }

def convert_all_tools(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    return [convert_mcp_tool_to_openai(t) for t in mcp_tools]
