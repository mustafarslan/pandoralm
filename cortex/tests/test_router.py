"""
Tests for Cognitive Router (Query Intent Classification) - Tiered Inference

Verifies that the QueryIntentClassifier correctly routes queries to:
- FACTUAL → Vector search (System 1: fast, Router layer)
- THEMATIC → Graph search (System 2: slow, Solver layer)
- RESEARCH → Deep research (System 2: external data)
- CODE_GENERATION → Code pipeline

Tiered Inference:
- Router: Uses 1B model (gemma3:1b) for fast classification
- Solver: Uses heavy model (deepseek-r1:8b) for complex reasoning
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.router import (
    IntentType,
    ClassificationResult,
    RouterClassification,
    QueryIntentClassifier,
    get_intent_classifier,
    INTENT_TO_QUERY_MODE,
)


class TestIntentType:
    """Test IntentType enum values."""
    
    def test_intent_types_exist(self):
        """Verify all expected intent types exist."""
        assert IntentType.FACTUAL.value == "factual"
        assert IntentType.THEMATIC.value == "thematic"
        assert IntentType.RESEARCH.value == "research"
        assert IntentType.CODE_GENERATION.value == "code_generation"
    
    def test_intent_to_query_mode_mapping(self):
        """Verify intent types map to correct query modes."""
        assert INTENT_TO_QUERY_MODE[IntentType.FACTUAL] == "vector"
        assert INTENT_TO_QUERY_MODE[IntentType.THEMATIC] == "graph"
        assert INTENT_TO_QUERY_MODE[IntentType.RESEARCH] == "research"
        assert INTENT_TO_QUERY_MODE[IntentType.CODE_GENERATION] == "vector"


class TestClassificationResult:
    """Test ClassificationResult dataclass."""
    
    def test_to_dict(self):
        """Verify to_dict returns correct structure."""
        result = ClassificationResult(
            intent=IntentType.FACTUAL,
            confidence=0.95,
            reasoning="Simple fact lookup",
            latency_ms=85.5,
            model_used="gpt-4o-mini",
        )
        
        d = result.to_dict()
        
        assert d["intent"] == "factual"
        assert d["confidence"] == 0.95
        assert d["reasoning"] == "Simple fact lookup"
        assert d["latency_ms"] == 85.5
        assert d["model_used"] == "gpt-4o-mini"


class TestRouterClassification:
    """Test RouterClassification model (simplified output for 1B models)."""
    
    def test_router_classification_no_reasoning(self):
        """Verify RouterClassification works without reasoning field (1B model optimization)."""
        # RouterClassification is designed for 1B models - no reasoning field
        result = RouterClassification(
            intent=IntentType.FACTUAL,
            confidence=0.9,
        )
        
        assert result.intent == IntentType.FACTUAL
        assert result.confidence == 0.9
        # Verify no reasoning attribute (this is the key difference from IntentClassification)
        assert not hasattr(result, 'reasoning') or getattr(result, 'reasoning', None) is None
    
    def test_router_classification_default_confidence(self):
        """Verify RouterClassification has sensible default confidence."""
        result = RouterClassification(intent=IntentType.THEMATIC)
        
        assert result.intent == IntentType.THEMATIC
        assert result.confidence == 0.8  # Default value


class TestQueryIntentClassifier:
    """Test QueryIntentClassifier with mocked LLM."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return QueryIntentClassifier(provider="openai", model="gpt-4o-mini")
    
    @pytest.mark.asyncio
    async def test_classify_factual_query(self, classifier):
        """Test: Simple fact lookups should return FACTUAL."""
        # Mock the _get_openai_client method to return our mock client
        with patch.object(classifier, '_get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                intent=IntentType.FACTUAL,
                confidence=0.95,
                reasoning="Simple fact lookup, single answer expected",
            )
            mock_get_client.return_value = mock_client
            
            result = await classifier.classify("What is the capital of France?")
            
            assert result.intent == IntentType.FACTUAL
            assert result.confidence == 0.95
            assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    async def test_classify_thematic_query(self, classifier):
        """Test: Relationship questions should return THEMATIC."""
        with patch.object(classifier, '_get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                intent=IntentType.THEMATIC,
                confidence=0.90,
                reasoning="Requires understanding relationships across documents",
            )
            mock_get_client.return_value = mock_client
            
            result = await classifier.classify(
                "How do the Q3 compliance changes impact our hiring policy?"
            )
            
            assert result.intent == IntentType.THEMATIC
            assert result.confidence == 0.90
    
    @pytest.mark.asyncio
    async def test_classify_research_query(self, classifier):
        """Test: Research requests should return RESEARCH."""
        with patch.object(classifier, '_get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                intent=IntentType.RESEARCH,
                confidence=0.88,
                reasoning="Requires external data gathering",
            )
            mock_get_client.return_value = mock_client
            
            result = await classifier.classify(
                "Research our competitors' pricing strategies"
            )
            
            assert result.intent == IntentType.RESEARCH
    
    @pytest.mark.asyncio  
    async def test_classify_code_generation_query(self, classifier):
        """Test: Code requests should return CODE_GENERATION."""
        with patch.object(classifier, '_get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = MagicMock(
                intent=IntentType.CODE_GENERATION,
                confidence=0.92,
                reasoning="User explicitly wants code output",
            )
            mock_get_client.return_value = mock_client
            
            result = await classifier.classify(
                "Write a Python function to parse JSON"
            )
            
            assert result.intent == IntentType.CODE_GENERATION
    
    @pytest.mark.asyncio
    async def test_classify_fallback_on_error(self, classifier):
        """Test: Classification errors should fallback to FACTUAL."""
        with patch.object(classifier, '_get_openai_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_get_client.return_value = mock_client
            
            # Create a simplified classifier that won't try semantic router first
            # to ensure we hit the LLM logic and fail there
            classifier.semantic_router = None
            
            result = await classifier.classify("Any query")
            
            assert result.intent == IntentType.FACTUAL
            assert result.confidence == 0.5
            assert "fallback" in result.reasoning.lower() or "error" in result.reasoning.lower()
            assert result.model_used == "fallback"


class TestQueryIntentClassifierIntegration:
    """
    Integration tests that actually call the LLM.
    
    These tests require OPENAI_API_KEY to be set and will incur costs.
    Skip in CI by using: pytest -m "not integration"
    """
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_factual_classification(self):
        """Integration: Real LLM should classify factual queries correctly."""
        classifier = get_intent_classifier()
        result = await classifier.classify("What is the capital of France?")
        
        assert result.intent == IntentType.FACTUAL
        assert result.latency_ms > 0
        assert result.latency_ms < 500  # Should be fast
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_thematic_classification(self):
        """Integration: Real LLM should classify thematic queries correctly."""
        classifier = get_intent_classifier()
        result = await classifier.classify(
            "What are the main themes across all our policy documents?"
        )
        
        assert result.intent == IntentType.THEMATIC


# Example queries for manual testing
EXAMPLE_QUERIES = {
    IntentType.FACTUAL: [
        "What is the capital of France?",
        "When was the last board meeting?",
        "Who is the CEO of the company?",
        "What does API stand for?",
    ],
    IntentType.THEMATIC: [
        "How do the Q3 compliance changes impact our engineering hiring policy?",
        "What are the main themes across all our policy documents?",
        "Explain the relationship between marketing strategy and sales",
        "Compare our product features with competitor X",
    ],
    IntentType.RESEARCH: [
        "Research our competitors' pricing strategies",
        "Find and summarize recent news about AI regulations",
        "Investigate market trends in fintech",
        "Gather data on customer satisfaction benchmarks",
    ],
    IntentType.CODE_GENERATION: [
        "Write a Python function to parse JSON",
        "Create a REST API endpoint for user registration",
        "Generate a SQL query to find duplicate records",
        "Write a bash script to backup the database",
    ],
}
