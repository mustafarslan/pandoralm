import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.stream import event_generator, StreamRequest
from app.services.graphrag.query_router import QueryContext, QueryMode
from app.api.protocols.vercel import StreamProtocol

@pytest.mark.asyncio
async def test_stream_triggers_meeting_and_graph():
    """
    Verify that the stream generator emits Generative UI triggers 
    when the QueryContext contains specific metadata.
    """
    
    # 1. Mock QueryRouter
    mock_router = AsyncMock()
    
    # 2. Mock Detection (Force Auto -> Hybrid)
    mock_router._detect_query_mode_llm.return_value = (QueryMode.HYBRID, None)
    
    # 3. Create a Rich QueryContext
    mock_context = QueryContext(
        mode=QueryMode.HYBRID,
        content="Here is the answer based on the meeting.",
        sources=[
            {
                "chunk_id": "c1",
                "metadata": {
                    "source_type": "meeting",
                    "file_id": "meeting_123",
                    "meeting_title": "Q3 Planning",
                    "start_time": 45.5
                }
            },
            {
                "chunk_id": "c2",
                "metadata": {
                    "source_type": "pdf",
                    "file_id": "doc_456"
                }
            }
        ],
        entities=[
            {"name": "Project X", "type": "Project"},
            {"name": "Alice", "type": "Person"}
        ],
        communities=[],
        confidence=0.9
    )
    
    mock_router.route_query.return_value = mock_context
    
    # 4. Patch get_query_router to return our mock
    with patch("app.api.v1.stream.get_query_router", return_value=mock_router):
        
        request = StreamRequest(query="What happened in Project X?", workspace_id="ws_1", mode="auto")
        
        # 5. Collect chunks
        chunks = []
        async for chunk in event_generator(request):
            chunks.append(chunk)
            
        # 6. Analyze Chunks
        meeting_trigger_found = False
        graph_trigger_found = False
        text_found = False
        
        for chunk in chunks:
            # Format is "2:[...]"
            if chunk.startswith("2:"):
                payload = json.loads(chunk[2:])
                event = payload[0]
                
                if event["type"] == "meeting_ref":
                    print(f"Found Meeting Trigger: {event}")
                    assert event["fileId"] == "meeting_123"
                    assert event["timestamp"] == 45.5
                    assert event["title"] == "Q3 Planning"
                    meeting_trigger_found = True
                    
                if event["type"] == "graph_viz":
                    print(f"Found Graph Trigger: {event}")
                    assert len(event["nodes"]) == 2
                    assert event["nodes"][0]["id"] == "Project X"
                    graph_trigger_found = True
                    
            if chunk.startswith("0:"):
                text_found = True
        
        assert meeting_trigger_found, "Meeting Reference trigger was NOT emitted"
        assert graph_trigger_found, "Graph Visualization trigger was NOT emitted"
        assert text_found, "Text stream missing"
        
if __name__ == "__main__":
    # verification via manual run
    asyncio.run(test_stream_triggers_meeting_and_graph())
