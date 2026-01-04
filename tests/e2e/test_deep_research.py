from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Since we are testing logic that depends on Celery and Playwright which are hard to run in unit tests 
# without heavy mocking or full env, we will mock the "Tools" layer.

@pytest.mark.asyncio
async def test_deep_research_agent_flow():
    """
    Test the DeepResearchAgent plan -> search -> scrape -> synthesize loop.
    We mock the actual network calls.
    """
    with patch("app.services.agent.researcher.SearchTool") as mock_search_cls, \
         patch("app.services.agent.researcher.AsyncWebTool") as mock_web_cls:
        
        # Setup mocks
        mock_search_tool = mock_search_cls.return_value
        mock_search_tool.search = AsyncMock(return_value=[
            {"title": "Result 1", "url": "http://example.com/1", "content": "foo"},
            {"title": "Result 2", "url": "http://example.com/2", "content": "bar"},
        ])
        
        mock_web_tool = mock_web_cls.return_value
        mock_web_tool.scrape = MagicMock(return_value="Scraping started")
        
        # Import Agent inside patch context to ensure mocks are used
        from app.services.agent.researcher import DeepResearchAgent
        
        agent = DeepResearchAgent()
        
        # Execute
        result = await agent.run("Test Topic")
        
        # Verify Plan/Search
        # Search called with generated queries (we mocked plan to return list)
        assert mock_search_tool.search.called
        assert len(result["sources"]) == 2
        
        # Verify Scrape
        # Should scrape unique URLs
        assert mock_web_tool.scrape.call_count == 2
        mock_web_tool.scrape.assert_any_call("http://example.com/1", layer_id="user_private")
        
        # Verify Synthesis
        assert "Report" in result["report"]

# We can also add a real integration test if we had a dedicated test env
