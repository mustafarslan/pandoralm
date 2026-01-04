import json
import asyncio
from typing import List, Dict, Any
from app.core.config import settings
from app.tools.search import SearchTool
from app.tools.web import AsyncWebTool

class DeepResearchAgent:
    """
    Orchestrates the Deep Research loop:
    1. Plan: Analyze query & generate search terms.
    2. Search: Use LinkUp/Tavily.
    3. Scrape: Use AsyncWebTool (Playwright/Celery) for deep dive.
    4. Ingest: Index content into Graph+Vector.
    5. Synthesize: Generate final answer.
    """
    
    def __init__(self):
        self.search_tool = SearchTool()
        self.web_tool = AsyncWebTool()
        
    async def run(self, topic: str, max_depth: int = 1) -> Dict[str, Any]:
        """
        Run the full research loop.
        """
        # Step 1: Plan
        search_queries = await self._plan_research(topic)
        
        # Step 2: Search
        all_results = []
        for query in search_queries[:3]: # Limit to top 3 queries
            results = await self.search_tool.search(query, max_results=3)
            all_results.extend(results)
            
        # Step 3: Select top URLs for Deep Scrape
        # Simple heuristic: top 2 unique URLs
        unique_urls = list({r['url'] for r in all_results if r.get('url')})[:2]
        
        # Step 4: Trigger Scrape & Ingest (Async)
        scrape_tasks = []
        for url in unique_urls:
            # This triggers the Celery task which ingests into Graph+Vector
            msg = self.web_tool.scrape(url, layer_id="user_private") 
            scrape_tasks.append({"url": url, "status": msg})
            
        # Note: In a real agent, we might wait for ingestion to complete 
        # before synthesis. For MVP/Async architecture, we synthesize 
        # based on Search Snippets first, and let the "Deep" knowledge 
        # be available for *subsequent* queries.
        
        # Step 5: Synthesize
        report = await self._synthesize(topic, all_results)
        
        return {
            "topic": topic,
            "report": report,
            "sources": all_results,
            "scraping_status": scrape_tasks
        }

    async def _plan_research(self, topic: str) -> List[str]:
        # Mock LLM call to generate search queries
        # In production, use your LLM service here
        return [topic, f"{topic} latest news", f"{topic} analysis"]

    async def _synthesize(self, topic: str, results: List[Dict[str, Any]]) -> str:
        # Mock synthesis
        context = "\n".join([f"- {r['title']}: {r['content']}" for r in results])
        return f"Research Report on {topic}\n\nBased on {len(results)} sources:\n{context[:500]}..."
