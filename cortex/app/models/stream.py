
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class StreamEventType(str, Enum):
    TOKEN = "token"             # Text token for the final answer
    THOUGHT = "thought"         # Reasoning step / internal thought
    TOOL_CALL = "tool_call"     # Agent deciding to call a tool
    TOOL_RESULT = "tool_result" # Result from a tool
    GRAPH = "graph_subgraph"    # Knowledge graph data for visualization
    ERROR = "error"
    DONE = "done"

class StreamEvent(BaseModel):
    event: StreamEventType
    data: Dict[str, Any]
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event string."""
        import json
        return f"event: {self.event.value}\ndata: {json.dumps(self.data)}\n\n"
