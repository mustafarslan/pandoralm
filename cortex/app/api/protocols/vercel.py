import json
from typing import Any, List, Dict, Optional

class StreamProtocol:
    """
    Implements the Vercel AI SDK Data Stream Protocol (v3.4+).
    
    Format:
    - Text: 0:"content"\n
    - Data: 2:[{"type":...}]\n
    - Error: 3:"error message"\n
    
    Phase 5.4: Extended with Generative UI triggers for Meeting Intelligence.
    """

    @staticmethod
    def text_chunk(content: str) -> str:
        """Format a text delta."""
        # JSON dump the string to handle escaping quotes/newlines safely
        return f'0:{json.dumps(content)}\n'

    @staticmethod
    def data_chunk(data: List[Dict[str, Any]]) -> str:
        """Format a data payload (tools, citations, UI triggers)."""
        return f'2:{json.dumps(data)}\n'

    @staticmethod
    def error_chunk(message: str) -> str:
        """Format an error message."""
        return f'3:{json.dumps(message)}\n'
    
    @staticmethod
    def thought(step: str, content: str, type_tier: str = "SYSTEM_1") -> str:
        """
        Create a logic trace chunk for the Thought Accordion.
        
        Args:
            step: The activity name (e.g., ROUTING, RETRIEVAL)
            content: The detailed log message
            type_tier: SYSTEM_1 (Fast) or SYSTEM_2 (Slow/Reasoning)
        """
        payload = [{
            "type": "thought",
            "step": step,
            "content": content,
            "tier": type_tier
        }]
        return f'2:{json.dumps(payload)}\n'
        
    # === Generative UI Helpers (Phase 5.4) ===
    
    @staticmethod
    def meeting_ref(file_id: str, timestamp: float, title: Optional[str] = None) -> str:
        """
        Create a meeting reference trigger for the MeetingPlayer component.
        
        When the frontend receives this payload, it should render
        a <MeetingPlayer /> component inside the chat bubble.
        
        Args:
            file_id: S3 object key or meeting ID
            timestamp: Start time in seconds to auto-seek
            title: Optional meeting title for display
            
        Returns:
            Vercel AI SDK Data Stream formatted string
        """
        payload = [{
            "type": "meeting_ref",
            "fileId": file_id,
            "timestamp": timestamp,
            "title": title
        }]
        return f'2:{json.dumps(payload)}\n'
    
    @staticmethod
    def graph_viz(
        nodes: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]],
        title: Optional[str] = None
    ) -> str:
        """
        Create a graph visualization trigger.
        
        Renders a force-directed graph in the chat window
        for code relationships or entity connections.
        """
        payload = [{
            "type": "graph_viz",
            "nodes": nodes,
            "edges": edges,
            "title": title
        }]
        return f'2:{json.dumps(payload)}\n'
    
    @staticmethod
    def code_block(
        code: str,
        language: str = "python",
        file_path: Optional[str] = None
    ) -> str:
        """
        Create an interactive code block trigger.
        
        Renders syntax-highlighted code with copy/expand functionality.
        """
        payload = [{
            "type": "code_block",
            "code": code,
            "language": language,
            "filePath": file_path
        }]
        return f'2:{json.dumps(payload)}\n'
    
    @staticmethod
    def citation(
        source_id: str,
        text: str,
        page: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> str:
        """
        Create a source citation trigger.
        
        Links to the original document/meeting/code with context.
        """
        payload = [{
            "type": "citation",
            "sourceId": source_id,
            "text": text,
            "page": page,
            "timestamp": timestamp
        }]
        return f'2:{json.dumps(payload)}\n'

