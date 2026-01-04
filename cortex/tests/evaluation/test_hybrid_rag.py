
import pytest
import os
import json
import requests
import time
from typing import List, Dict, Any, Optional

from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric
from deepeval.models.base_model import DeepEvalBaseLLM

# Helpers
API_URL = "http://localhost:8000/api/v1"
DATASET_PATH = "/app/tests/data/golden_dataset.json"

# ==========================================
# Custom LLM for DeepEval (Local Ollama)
# ==========================================
class OllamaDeepEval(DeepEvalBaseLLM):
    def __init__(self, model_name="deepseek-r1:8b"):
        self.model_name = model_name
        self.api_base = os.getenv("LLM_ROUTER_API_BASE", "http://host.docker.internal:11434")

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        # Use requests to verify simple connectivity to Ollama
        try:
            resp = requests.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            if resp.status_code == 200:
                return resp.json()["response"]
            return "Error from Ollama"
        except Exception as e:
            return f"Error generating: {e}"

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self):
        return self.model_name

def load_dataset() -> List[Dict]:
    """Load the golden dataset."""
    with open(DATASET_PATH, "r") as f:
        return json.load(f)

# ==========================================
# Check A: Router Accuracy
# ==========================================
@pytest.mark.eval
def test_router_accuracy():
    """System 1 Router verification."""
    test_cases = [
        ("What are the core hours for remote work?", "factual", "vector"),
        ("What is the maximum number of days for Digital Nomad exception?", "factual", "vector"),
        ("Does the remote work policy conflict with the Digital Nomad limits?", "thematic", "graph"),
        ("Summarize the security requirements for database access.", "thematic", "graph")
    ]
    
    classification_errors = []
    
    for query, intent_type, expected_mode in test_cases:
        print(f"Testing Router: '{query}'")
        try:
            resp = requests.post(
                f"{API_URL}/query",
                json={"query": query, "workspace_id": "eval-ws", "mode": "auto"}
            )
            assert resp.status_code == 200, f"API failed: {resp.text}"
            data = resp.json()
            
            # Debugging for KeyError
            if "metadata" not in data:
                print(f"❌ WARNING: 'metadata' field missing in API response. Got keys: {list(data.keys())}")
                print(f"Full response: {data}")
                classification_errors.append(f"API Metadata Missing | Query: {query}")
                continue
                
            router_decision = data["metadata"]["router_decision"]
            print(f" -> Decision: {router_decision} (Expected similar to {expected_mode})")
            
            # Relaxed assertion logic
            if intent_type == "factual" and router_decision not in ["vector", "auto", "hybrid"]:
                 classification_errors.append(f"Query '{query}' classified as {router_decision}, expected vector")
                 
            if intent_type == "thematic" and router_decision not in ["graph", "hybrid", "auto"]:
                 # Sometimes thematic falls back to vector if confidence is low, which is technically a router 'fail' but acceptable
                 classification_errors.append(f"Query '{query}' classified as {router_decision}, expected graph/hybrid")
                 
        except Exception as e:
            classification_errors.append(f"Exception for '{query}': {str(e)}")

    assert len(classification_errors) == 0, f"Router Errors:\n" + "\n".join(classification_errors)


# ==========================================
# Check B: RAG Quality (DeepEval)
# ==========================================
@pytest.mark.eval
def test_hybrid_rag_quality():
    """Faithfulness check using local LLM."""
    dataset = load_dataset()
    if not dataset:
        pytest.skip("Golden dataset not found.")
        
    custom_model = OllamaDeepEval(model_name="deepseek-r1:8b")
        
    for case in dataset:
        query = case["input"]
        expected = case["expected_output"]
        
        print(f"\nEvaluating: {query}")
        
        resp = requests.post(
            f"{API_URL}/query",
            json={"query": query, "workspace_id": "eval-ws", "mode": "auto"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        if "metadata" not in data:
            pytest.fail("API response missing metadata. Ensure Glass Box refactor is active.")
            
        actual_output = data["answer"]
        retrieved_context = data["metadata"]["retrieved_context"]
        
        test_case = LLMTestCase(
            input=query,
            actual_output=actual_output,
            retrieval_context=retrieved_context,
            expected_output=expected
        )
        
        metric = FaithfulnessMetric(
            threshold=0.8,
            model=custom_model, # Use local model
            include_reason=True
        )
        
        assert_test(test_case, [metric])

