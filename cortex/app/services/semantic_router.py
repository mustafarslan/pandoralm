import os
from typing import List, Tuple
from semantic_router import Route
from semantic_router.encoders import HuggingFaceEncoder
from semantic_router.layer import RouteLayer

class SemanticRouterService:
    """
    Local Semantic Router for fast (<50ms) intent classification.
    """
    
    def __init__(self):
        # Initialize encoder with local cache
        cache_dir = os.getenv("MODEL_CACHE_DIR", "/app/models")
        self.encoder = HuggingFaceEncoder(
            name="sentence-transformers/all-MiniLM-L6-v2",
            cache_folder=cache_dir
        )
        
        # Define Routes
        self.routes = [
            Route(
                name="internal_knowledge",
                utterances=[
                    "What is our policy on remote work?",
                    "How do I reset my password?",
                    "What are the benefits for 2024?",
                    "Explain the onboarding process",
                    "Who is the CEO?",
                    "What is the capital of France?", # Basic facts often go here/vector
                ],
            ),
            Route(
                name="codebase",
                utterances=[
                    "How does the auth middleware work?",
                    "Fix the bug in main.py",
                    "Write a python function to parse JSON",
                    "Explain the code in services/router.py",
                    "Where is the User model defined?",
                ],
            ),
            Route(
                name="web_research",
                utterances=[
                    "Research the latest AI regulations",
                    "Find news about Apple stock",
                    "What are the competitors of PandoraLM?",
                    "Search for the latest React clean architecture patterns",
                    "Who won the Super Bowl?",
                ],
            ),
        ]
        
        self.layer = RouteLayer(encoder=self.encoder, routes=self.routes)
        
    def route(self, query: str) -> Tuple[str, float]:
        """
        Route the query to the best matching intent.
        Returns (route_name, confidence).
        """
        try:
            result = self.layer(query)
            if result.name:
                return result.name, 1.0 # Semantic router doesn't always expose score easily in simple call
            return "general_chat", 0.0 # Fallback
        except Exception as e:
            print(f"Routing error: {e}")
            return "general_chat", 0.0

# Singleton
_semantic_router = None

def get_semantic_router():
    global _semantic_router
    if _semantic_router is None:
        _semantic_router = SemanticRouterService()
    return _semantic_router
