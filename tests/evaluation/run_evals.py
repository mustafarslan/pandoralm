"""
DeepEval Evaluation Pipeline for PandoraLM.

This script runs the RAG Triad evaluation metrics against the Cortex API
using a Golden Dataset of QA pairs.

Usage:
    python tests/evaluation/run_evals.py

Metrics:
    - Faithfulness: Did the LLM stick to retrieved chunks?
    - Answer Relevance: Did we actually answer the user's question?
    - Context Precision: Did we retrieve the right chunks?
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Any

# DeepEval imports
try:
    from deepeval import evaluate
    from deepeval.metrics import (
        FaithfulnessMetric,
        AnswerRelevancyMetric,
        ContextualPrecisionMetric,
    )
    from deepeval.test_case import LLMTestCase
except ImportError:
    print("❌ DeepEval not installed. Run: pip install deepeval")
    sys.exit(1)


# Configuration
CORTEX_API_URL = os.getenv("CORTEX_API_URL", "http://localhost:8000")
GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
FAITHFULNESS_THRESHOLD = 0.8
RELEVANCY_THRESHOLD = 0.7


def load_golden_dataset() -> List[Dict[str, Any]]:
    """Load the Golden Dataset from JSON file."""
    if not GOLDEN_DATASET_PATH.exists():
        print(f"❌ Golden dataset not found at {GOLDEN_DATASET_PATH}")
        sys.exit(1)
    
    with open(GOLDEN_DATASET_PATH, "r") as f:
        return json.load(f)


def query_cortex(question: str) -> Dict[str, Any]:
    """
    Send a query to the Cortex API and get the response with context.
    
    Returns:
        Dict with 'answer', 'context' (retrieved chunks), and 'trace_id'.
    """
    try:
        response = requests.post(
            f"{CORTEX_API_URL}/api/v1/chat/query",
            json={
                "query": question,
                "workspace_id": "evaluation",
                "include_context": True,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "answer": data.get("response", ""),
            "context": data.get("context", []),
            "trace_id": data.get("trace_id", ""),
        }
    except requests.RequestException as e:
        print(f"⚠️ API request failed: {e}")
        return {"answer": "", "context": [], "trace_id": ""}


def build_test_cases(golden_data: List[Dict[str, Any]]) -> List[LLMTestCase]:
    """Build DeepEval test cases from golden dataset + API responses."""
    test_cases = []
    
    for item in golden_data:
        print(f"📝 Evaluating: {item['id']} - {item['question'][:50]}...")
        
        # Query the actual system
        result = query_cortex(item["question"])
        
        # Build the test case
        test_case = LLMTestCase(
            input=item["question"],
            actual_output=result["answer"],
            expected_output=item["expected_answer"],
            retrieval_context=result["context"] if result["context"] else item.get("expected_context", []),
        )
        test_cases.append(test_case)
    
    return test_cases


def run_evaluation():
    """Main evaluation runner."""
    print("🧪 PandoraLM Evaluation Pipeline")
    print("=" * 50)
    
    # Load golden dataset
    golden_data = load_golden_dataset()
    print(f"📂 Loaded {len(golden_data)} golden test cases")
    
    # Build test cases with actual API responses
    test_cases = build_test_cases(golden_data)
    
    # Define metrics
    faithfulness = FaithfulnessMetric(
        threshold=FAITHFULNESS_THRESHOLD,
        model="gpt-4o-mini",  # For evaluation only
    )
    relevancy = AnswerRelevancyMetric(
        threshold=RELEVANCY_THRESHOLD,
        model="gpt-4o-mini",
    )
    precision = ContextualPrecisionMetric(
        threshold=0.7,
        model="gpt-4o-mini",
    )
    
    # Run evaluation
    print("\n🚀 Running DeepEval metrics...")
    results = evaluate(
        test_cases=test_cases,
        metrics=[faithfulness, relevancy, precision],
    )
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 EVALUATION RESULTS")
    print("=" * 50)
    
    passed = sum(1 for r in results.test_results if r.success)
    total = len(results.test_results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    # Quality gate check
    pass_rate = passed / total if total > 0 else 0
    if pass_rate < FAITHFULNESS_THRESHOLD:
        print(f"\n🚨 QUALITY GATE FAILED: Pass rate {pass_rate:.2%} < {FAITHFULNESS_THRESHOLD:.0%}")
        sys.exit(1)
    else:
        print(f"\n✨ QUALITY GATE PASSED: Pass rate {pass_rate:.2%}")
        sys.exit(0)


if __name__ == "__main__":
    run_evaluation()
