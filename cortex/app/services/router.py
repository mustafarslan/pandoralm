"""
Cognitive Router - Query Intent Classification (Tiered Inference)

Implements Kahneman's System 1 vs System 2 thinking for query routing:

System 1 (Fast): FACTUAL queries → Vector search
System 2 (Slow): THEMATIC/RESEARCH queries → Graph/Agentic search

Tiered Inference Architecture:
- Router: Fast 1B model (gemma3:1b) for classification (<300ms)
- Solver: Heavy reasoning model (deepseek-r1:8b) for generation (5-60s)

Supports multiple LLM providers:
- OpenAI (gpt-4o-mini) - Cloud-based, fast
- Ollama (gemma3:1b, deepseek-r1:8b, etc) - Local, private
"""
import time
import logging
import re
import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Query intent classification types."""
    FACTUAL = "factual"           # Simple fact lookup → Vector search
    THEMATIC = "thematic"         # Relationship/theme analysis → Graph search
    RESEARCH = "research"         # Deep research, external data → Agentic
    AGENTIC = "agent"             # Multi-step Agent execution (Personas)
    CODE_GENERATION = "code_generation"  # Code output expected


class LLMProvider(str, Enum):
    """Supported LLM providers for Cognitive Router."""
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass
class ClassificationResult:
    """Result of query intent classification."""
    intent: IntentType
    confidence: float
    reasoning: str
    latency_ms: float
    model_used: str
    provider: str = "unknown"
    
    def to_dict(self) -> dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "latency_ms": self.latency_ms,
            "model_used": self.model_used,
            "provider": self.provider,
        }


class RouterClassification(BaseModel):
    """
    Minimal structured output for Router classification (optimized for 1B models).
    
    Note: No 'reasoning' field - 1B models often hallucinate or break JSON
    when asked to explain themselves. We only need the label and confidence.
    """
    intent: IntentType = Field(
        description="The classified intent type for the query"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, default=0.8,
        description="Confidence score between 0 and 1"
    )


class IntentClassification(BaseModel):
    """Structured output for LLM classification (full version with reasoning)."""
    intent: IntentType = Field(
        description="The classified intent type for the query"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score between 0 and 1"
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )


# Few-shot examples for the classifier
FEW_SHOT_EXAMPLES = """
Examples of intent classification:

Query: "What is the capital of France?"
Intent: FACTUAL
Reasoning: Simple fact lookup, single answer expected

Query: "How do the Q3 compliance changes impact our engineering hiring policy?"
Intent: THEMATIC
Reasoning: Requires understanding relationships across multiple documents (compliance + hiring)

Query: "Research our competitors' pricing strategies and market positioning"
Intent: RESEARCH
Reasoning: Requires external data gathering and multi-step analysis

Query: "Write a Python function to parse JSON and validate schema"
Intent: CODE_GENERATION
Reasoning: User explicitly wants code output

Query: "What are the main themes across all our policy documents?"
Intent: THEMATIC
Reasoning: Requires aggregating and synthesizing information from multiple sources

Query: "When was the last board meeting?"
Intent: FACTUAL
Reasoning: Simple date lookup, specific fact retrieval

Query: "Explain the relationship between our marketing strategy and sales performance"
Intent: THEMATIC
Reasoning: Requires understanding connections between different business areas

Query: "Find and summarize recent news about AI regulations"
Intent: RESEARCH  
Reasoning: Requires external web search and synthesis
"""

CLASSIFICATION_PROMPT = """You are a query intent classifier for an enterprise RAG system.

Your task is to classify the user's query into one of four intent types:

1. **FACTUAL**: Simple fact retrieval. The answer exists in a single document chunk.
   - "What is X?", "When did Y happen?", "Who is Z?"
   
2. **THEMATIC**: Requires understanding relationships or themes across multiple documents.
   - "How does X relate to Y?", "What are the themes?", "Compare A and B"
   
3. **RESEARCH**: Requires external data, web search, or multi-step investigation.
   - "Research X", "Find latest news about Y", "Investigate competitor Z"
   
4. **CODE_GENERATION**: User wants code output.
   - "Write code for X", "Create a function that Y", "Generate script to Z"

{examples}

Now classify this query:
Query: "{query}"

You MUST respond with a valid JSON object in this exact format:
{{"intent": "FACTUAL|THEMATIC|RESEARCH|CODE_GENERATION", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

IMPORTANT: Only output the JSON, nothing else."""


# Ultra-simplified prompt for Router (1B models)
# Key optimizations for small models:
# 1. No reasoning field - 1B models hallucinate when explaining
# 2. Minimal instructions - short context window
# 3. Explicit JSON format - no ambiguity
ROUTER_CLASSIFICATION_PROMPT = """You are a JSON classifier. Output strictly JSON. No markdown. No thinking.

Schema: {"intent": "factual"|"thematic"|"research"|"code_generation", "confidence": 0.0-1.0}

Rules:
- factual: "What is X?", simple fact questions
- thematic: "How does X relate to Y?", cross-document analysis  
- research: "Research X", external data needed
- code_generation: "Write code for X"

Query: "{query}"

JSON:"""

# Legacy prompt kept for backward compatibility
SIMPLE_CLASSIFICATION_PROMPT = """Classify this query into one category:

Categories:
- FACTUAL: Simple fact questions ("What is X?", "When did Y happen?")
- THEMATIC: Relationship/theme questions ("How does X relate to Y?", "Compare A and B")
- RESEARCH: External research needed ("Research X", "Find news about Y")
- CODE_GENERATION: Code requests ("Write code for X", "Create a function")

Query: "{query}"

Respond with JSON only:
{{"intent": "CATEGORY_NAME", "confidence": 0.8, "reasoning": "why"}}"""


class QueryIntentClassifier:
    """
    LLM-based query intent classifier (Tiered Inference - Router Layer).
    
    This is the ROUTER component of the tiered inference architecture.
    It uses a fast, lightweight model (1B parameters) for classification.
    
    Supports multiple providers:
    - OpenAI: Uses instructor for structured output (gpt-4o-mini ~100ms)
    - Ollama: Uses local 1B models for fast classification (gemma3:1b ~300ms)
    
    Configuration via environment variables:
    - LLM_PROVIDER: "openai" or "ollama"
    - LLM_ROUTER_MODEL: Fast model for classification (e.g., "gemma3:1b")
    - LLM_ROUTER_API_BASE: Ollama server URL for router
    
    Architecture Note:
        Do NOT use reasoning models (deepseek-r1, o1, etc) for the Router.
        They add "Thinking" latency that defeats the purpose of fast routing.
    """
    
    def __init__(
        self,
        provider: str = None,
        model: str = None,
    ):
        # Use new tiered inference settings, fallback to legacy for compatibility
        self.provider = LLMProvider(provider or settings.LLM_PROVIDER)
        self.model = model or settings.LLM_ROUTER_MODEL
        self._openai_client = None
        self._ollama_client = None
        
        logger.info(f"Cognitive Router (Tiered) initialized: provider={self.provider.value}, router_model={self.model}")
    
    def _get_openai_client(self):
        """Lazy initialization of instructor-patched OpenAI client."""
        if self._openai_client is None:
            try:
                import instructor
                from openai import OpenAI
                
                base_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self._openai_client = instructor.from_openai(base_client)
            except ImportError as e:
                logger.error(f"Failed to import instructor/openai: {e}")
                raise ImportError(
                    "instructor and openai packages required. "
                    "Install with: pip install instructor openai"
                )
        return self._openai_client
    
    def _get_ollama_client(self):
        """Lazy initialization of Ollama client for Router."""
        if self._ollama_client is None:
            try:
                import httpx
                # Use new LLM_ROUTER_API_BASE setting
                base_url = settings.LLM_ROUTER_API_BASE
                self._ollama_client = httpx.Client(
                    base_url=base_url,
                    timeout=30.0,  # Reduced timeout for fast router model
                )
                logger.debug(f"Router Ollama client initialized: {base_url}")
            except ImportError as e:
                logger.error(f"Failed to import httpx: {e}")
                raise ImportError("httpx package required for Ollama support")
        return self._ollama_client
    
    def _parse_llm_response(self, text: str) -> IntentClassification:
        """Parse LLM response to extract JSON classification."""
        # Try to extract JSON from response
        text = text.strip()
        
        # Handle thinking tags from deepseek-r1
        if "<think>" in text:
            # Extract content after </think>
            parts = text.split("</think>")
            if len(parts) > 1:
                text = parts[-1].strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        try:
            data = json.loads(text)
            
            # Normalize intent value
            intent_str = data.get("intent", "FACTUAL").upper()
            intent_str = intent_str.replace("_", "_")  # Normalize
            
            # Map to IntentType
            intent_map = {
                "FACTUAL": IntentType.FACTUAL,
                "THEMATIC": IntentType.THEMATIC,
                "RESEARCH": IntentType.RESEARCH,
                "AGENTIC": IntentType.AGENTIC,
                "AGENT": IntentType.AGENTIC,
                "CODE_GENERATION": IntentType.CODE_GENERATION,
                "CODE": IntentType.CODE_GENERATION,  # Common shorthand
            }
            
            intent = intent_map.get(intent_str, IntentType.FACTUAL)
            confidence = float(data.get("confidence", 0.8))
            reasoning = data.get("reasoning", "Classified by LLM")
            
            return IntentClassification(
                intent=intent,
                confidence=min(max(confidence, 0.0), 1.0),
                reasoning=reasoning,
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}, text={text[:100]}")
            # Default fallback
            return IntentClassification(
                intent=IntentType.FACTUAL,
                confidence=0.5,
                reasoning=f"Parse error, defaulting to FACTUAL: {str(e)[:50]}",
            )
    
    async def _classify_with_openai(
        self,
        query: str,
        conversation_history: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify using OpenAI with instructor."""
        import asyncio
        
        start_time = time.time()
        client = self._get_openai_client()
        
        prompt = CLASSIFICATION_PROMPT.format(
            examples=FEW_SHOT_EXAMPLES,
            query=query,
        )
        
        if conversation_history:
            prompt += f"\n\nConversation context: {conversation_history}"
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=self.model,
                response_model=IntentClassification,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=200,
            )
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ClassificationResult(
            intent=result.intent,
            confidence=result.confidence,
            reasoning=result.reasoning,
            latency_ms=latency_ms,
            model_used=self.model,
            provider="openai",
        )
    
    async def _classify_with_ollama(
        self,
        query: str,
        conversation_history: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Classify using local Ollama model (Router layer).
        
        Uses the ultra-simplified ROUTER_CLASSIFICATION_PROMPT optimized for
        1B models to achieve <300ms classification latency.
        """
        import asyncio
        
        start_time = time.time()
        client = self._get_ollama_client()
        
        # Use ultra-simplified prompt for 1B router models (no reasoning field)
        prompt = ROUTER_CLASSIFICATION_PROMPT.format(query=query)
        
        if conversation_history:
            prompt += f"\n\nContext: {conversation_history}"
        
        logger.info(f"Router calling Ollama: model={self.model}, url={settings.LLM_ROUTER_API_BASE}")
        
        loop = asyncio.get_event_loop()
        
        def call_ollama():
            request_body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 100,  # Reduced for router - only need short JSON
                }
            }
            logger.debug(f"Router Ollama request: {request_body}")
            
            response = client.post(
                "/api/generate",
                json=request_body,
            )
            response.raise_for_status()
            return response.json()
        
        result = await loop.run_in_executor(None, call_ollama)
        
        latency_ms = (time.time() - start_time) * 1000
        response_text = result.get("response", "")
        
        # Log response for debugging
        logger.info(f"Router response length: {len(response_text)}, latency: {latency_ms:.0f}ms")
        logger.debug(f"Router full response: {response_text}")
        
        if not response_text:
            # Check if there's a thinking field (some models put response there)
            thinking = result.get("thinking", "")
            logger.warning(f"Empty response, thinking field length: {len(thinking)}")
            
            # Try to extract JSON from thinking
            if thinking:
                response_text = thinking
        
        # Parse the response (handles missing reasoning field gracefully)
        classification = self._parse_llm_response(response_text)
        
        # For router, reasoning is optional - use default if not provided
        reasoning = getattr(classification, 'reasoning', None) or "Classified by router model"
        
        return ClassificationResult(
            intent=classification.intent,
            confidence=classification.confidence,
            reasoning=reasoning,
            latency_ms=latency_ms,
            model_used=self.model,
            provider="ollama",
        )
    
    async def classify(
        self,
        query: str,
        conversation_history: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Classify a query's intent using the configured LLM provider.
        
        Args:
            query: The user's query
            conversation_history: Optional summary of conversation context
            
        Returns:
            ClassificationResult with intent, confidence, reasoning, and latency
        """
        start_time = time.time()
        
        try:
            # 0. Try Semantic Router (Fastest, Local)
            try:
                from app.services.semantic_router import get_semantic_router
                semantic_router = get_semantic_router()
                route, confidence = semantic_router.route(query)
                
                if route != "general_chat" and confidence > 0.8:
                    # Map route names to IntentType
                    route_map = {
                        "internal_knowledge": IntentType.FACTUAL, # Or THEMATIC depending
                        "codebase": IntentType.CODE_GENERATION,
                        "web_research": IntentType.RESEARCH
                    }
                    if route in route_map:
                        latency_ms = (time.time() - start_time) * 1000
                        return ClassificationResult(
                            intent=route_map[route],
                            confidence=confidence,
                            reasoning=f"Semantic Router matched '{route}'",
                            latency_ms=latency_ms,
                            model_used="semantic-router",
                            provider="local"
                        )
            except Exception as e:
                logger.warning(f"Semantic Router failed: {e}")

            if self.provider == LLMProvider.OPENAI:
                return await self._classify_with_openai(query, conversation_history)
            elif self.provider == LLMProvider.OLLAMA:
                return await self._classify_with_ollama(query, conversation_history)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Classification failed ({self.provider.value}), defaulting to FACTUAL: {e}"
            )
            
            # Fallback to FACTUAL on error
            return ClassificationResult(
                intent=IntentType.FACTUAL,
                confidence=0.5,
                reasoning=f"Fallback due to {self.provider.value} error: {str(e)[:100]}",
                latency_ms=latency_ms,
                model_used="fallback",
                provider="fallback",
            )
    
    def classify_sync(
        self,
        query: str,
        conversation_history: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Synchronous version of classify for non-async contexts.
        """
        import asyncio
        return asyncio.run(self.classify(query, conversation_history))


# Singleton instance
_classifier: Optional[QueryIntentClassifier] = None


def get_intent_classifier() -> QueryIntentClassifier:
    """Get or create the intent classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = QueryIntentClassifier()
    return _classifier


def reset_intent_classifier():
    """Reset the singleton (useful for testing or reconfiguration)."""
    global _classifier
    _classifier = None


# Map IntentType to QueryMode for integration with existing router
INTENT_TO_QUERY_MODE = {
    IntentType.FACTUAL: "vector",
    IntentType.THEMATIC: "graph",
    IntentType.RESEARCH: "research",  # Triggers deep research
    IntentType.AGENTIC: "agent",      # Triggers Orchestrator
    IntentType.CODE_GENERATION: "vector",  # Search code chunks
}
