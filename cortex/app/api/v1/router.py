"""
Cognitive Router Endpoint - Test intent classification
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.router import get_intent_classifier, IntentType

router = APIRouter()


class ClassifyRequest(BaseModel):
    """Request to classify a query intent."""
    query: str
    conversation_history: Optional[str] = None


class ClassifyResponse(BaseModel):
    """Response with classification result."""
    query: str
    intent: str
    confidence: float
    reasoning: str
    latency_ms: float
    model_used: str
    provider: str


@router.post("/classify", response_model=ClassifyResponse)
async def classify_query(request: ClassifyRequest) -> ClassifyResponse:
    """
    Classify a query's intent using the Cognitive Router.

    This endpoint tests the LLM-based intent classification without
    performing the actual search. Useful for debugging and testing.

    Returns:
        - intent: FACTUAL, THEMATIC, RESEARCH, or CODE_GENERATION
        - confidence: 0.0 to 1.0
        - reasoning: Explanation of classification
        - latency_ms: Time taken for classification
        - provider: "openai" or "ollama"
    """
    classifier = get_intent_classifier()
    result = await classifier.classify(
        query=request.query,
        conversation_history=request.conversation_history,
    )

    return ClassifyResponse(
        query=request.query,
        intent=result.intent.value,
        confidence=result.confidence,
        reasoning=result.reasoning,
        latency_ms=result.latency_ms,
        model_used=result.model_used,
        provider=result.provider,
    )


@router.get("/config")
async def router_config() -> dict:
    """Get current Cognitive Router configuration."""
    from app.core.config import settings

    return {
        "provider": settings.ROUTER_LLM_PROVIDER,
        "model": settings.ROUTER_LLM_MODEL,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "openai_configured": bool(settings.OPENAI_API_KEY),
    }


@router.get("/test")
async def test_classification() -> dict:
    """
    Quick test of the Cognitive Router with sample queries.

    Returns classification results for 4 sample queries.
    """
    classifier = get_intent_classifier()

    test_queries = [
        ("What is the capital of France?", IntentType.FACTUAL),
        ("How do compliance changes impact hiring?", IntentType.THEMATIC),
        ("Research competitor pricing", IntentType.RESEARCH),
        ("Write a Python function", IntentType.CODE_GENERATION),
    ]

    results = []
    for query, expected in test_queries:
        result = await classifier.classify(query)
        results.append({
            "query": query,
            "expected": expected.value,
            "actual": result.intent.value,
            "correct": result.intent == expected,
            "confidence": result.confidence,
            "latency_ms": result.latency_ms,
        })

    correct = sum(1 for r in results if r["correct"])

    return {
        "provider": classifier.provider.value,
        "model": classifier.model,
        "accuracy": f"{correct}/{len(results)}",
        "results": results,
    }
