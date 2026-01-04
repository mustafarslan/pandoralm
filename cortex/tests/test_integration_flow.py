
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.v1.stream import event_generator, StreamRequest
from app.services.graphrag.query_router import QueryMode
# We don't import StreamProtocol here to avoid dependency issues if not needed, 
# but we will check string outputs or mock the protocol if easier.

@pytest.mark.asyncio
async def test_factual_flow_dispatch():
    """
    Test that a FACTUAL query routes to QueryMode.VECTOR
    and calls route_query with the correct mode.
    """
    with patch("app.api.v1.stream.get_query_router") as mock_get_router:
        router_instance = AsyncMock()
        mock_get_router.return_value = router_instance
        
        # Setup: Detects VECTOR mode
        router_instance._detect_query_mode_llm.return_value = (QueryMode.VECTOR, "Factual lookup")
        
        # Setup: Route query returns a mock context
        mock_context = MagicMock()
        # Ensure properties expected by stream.py are present
        mock_context.sources = [] 
        mock_context.entities = []
        mock_context.content = "Paris is the capital of France."
        router_instance.route_query.return_value = mock_context

        # Request with auto mode
        req = StreamRequest(query="What is capital of France?", workspace_id="default", mode="auto")
        
        # Execute generator
        events = []
        async for event in event_generator(req):
            events.append(event)
            
        # Verify Router was called correctly
        router_instance._detect_query_mode_llm.assert_called_once()
        router_instance.route_query.assert_called_once()
        
        # Check arguments: mode should be VECTOR
        call_args = router_instance.route_query.call_args
        assert call_args.kwargs['mode'] == QueryMode.VECTOR
        
        # Verify "Thought" event indicating mode selection
        # StreamProtocol.data_chunk returns a string formatted for Vercel
        # We check if one of the chunks contains "VECTOR"
        thought_events = [e for e in events if "VECTOR" in str(e)]
        assert len(thought_events) > 0

@pytest.mark.asyncio
async def test_thematic_flow_dispatch():
    """
    Test that a THEMATIC query routes to QueryMode.GRAPH
    """
    with patch("app.api.v1.stream.get_query_router") as mock_get_router:
        router_instance = AsyncMock()
        mock_get_router.return_value = router_instance
        
        # Setup: Detects GRAPH mode
        router_instance._detect_query_mode_llm.return_value = (QueryMode.GRAPH, "Thematic analysis")
        
        mock_context = MagicMock()
        mock_context.sources = []
        mock_context.entities = [{"name": "Entity1", "type": "Topic"}]
        mock_context.content = "The theme is..."
        router_instance.route_query.return_value = mock_context

        req = StreamRequest(query="What are the themes?", workspace_id="default", mode="auto")
        
        events = []
        async for event in event_generator(req):
            events.append(event)
            
        # Verify call to route_query with GRAPH mode
        router_instance.route_query.assert_called_once()
        assert router_instance.route_query.call_args.kwargs['mode'] == QueryMode.GRAPH

@pytest.mark.asyncio
async def test_agent_flow_dispatch():
    """
    Test that a RESEARCH query routes to ResearchAgent
    """
    with patch("app.api.v1.stream.get_query_router") as mock_get_router, \
         patch("app.api.v1.stream.ResearchAgent") as mock_agent_cls:
             
        router_instance = AsyncMock()
        mock_get_router.return_value = router_instance
        
        # Setup: Detects RESEARCH mode
        # Note: In stream.py, it checks return value of _detect_query_mode_llm
        # The enum might capture "research" as a valid mode? 
        # Let's assume QueryMode has RESEARCH or stream.py handles the string value.
        # Looking at stream.py line 39: `mode = detection_mode.value`
        # And line 52: `if mode == "research":`
        
        # We need to mock the enum if QueryMode doesn't have RESEARCH, 
        # or just return a mock object that has .value = "research"
        mock_mode = MagicMock()
        mock_mode.value = "research"
        router_instance._detect_query_mode_llm.return_value = (mock_mode, "Need to research")
        
        # Setup Agent
        mock_agent_instance = MagicMock()
        mock_agent_cls.return_value = mock_agent_instance
        
        # Setup Agent stream
        # execute_stream is an async generator
        async def mock_agent_stream(*args, **kwargs):
            yield MagicMock(event=MagicMock(value="thought"), data={"content": "Searching web..."})
            yield MagicMock(event=MagicMock(value="token"), data={"text": "Found info."})
            
        mock_agent_instance.execute_stream = mock_agent_stream
        
        req = StreamRequest(query="Research X", workspace_id="default", mode="auto")
        
        events = []
        async for event in event_generator(req):
            events.append(event)
            
        # Verify route_query was NOT called
        router_instance.route_query.assert_not_called()
        
        # Verify Agent was instantiated and executed
        mock_agent_cls.assert_called_once()
        # We can't easily assert assert_called on the generator method itself easily without tracking
        # but the fact we got events implies it was called.
        assert len(events) > 0
