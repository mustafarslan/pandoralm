import os
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

class SearchTool:
    """
    Search tool using LinkUp (primary) or Tavily (fallback).
    """
    
    def __init__(self):
        self.linkup_key = os.getenv("LINKUP_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        
    async def search(self, query: str, depth: str = "standard", max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Execute search and return standardized results.
        [ {title, url, content, score}, ... ]
        """
        if self.linkup_key:
            return await self._search_linkup(query, depth, max_results)
        elif self.tavily_key:
            return await self._search_tavily(query, depth, max_results)
        else:
            return self._mock_search(query, max_results)
            
    async def _search_linkup(self, query: str, depth: str, max_results: int) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.linkup.so/v1/search",
                params={"q": query, "depth": depth, "limit": max_results},
                headers={"Authorization": f"Bearer {self.linkup_key}"}
            )
            response.raise_for_status()
            data = response.json()
            # Transform to standard format
            return [
                {
                    "title": item.get("name") or item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("snippet") or item.get("content"),
                    "score": 0.9 # LinkUp doesn't always return score
                }
                for item in data.get("results", [])
            ]

    async def _search_tavily(self, query: str, depth: str, max_results: int) -> List[Dict[str, Any]]:
        # Tavily implementation
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "advanced" if depth == "deep" else "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False
        }
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                    "score": item.get("score")
                }
                for item in data.get("results", [])
            ]

    def _mock_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        return [
            {
                "title": f"Mock Result for {query} ({i})",
                "url": f"https://example.com/search?q={query}&id={i}",
                "content": f"This is a simulated search result for {query}. Please configure LINKUP_API_KEY or TAVILY_API_KEY.",
                "score": 0.8 - (i * 0.1)
            }
            for i in range(max_results)
        ]
