
import json
import os
import argparse
from typing import List, Dict
import requests

# Constants
# Constants
LLM_API_BASE = os.getenv("LLM_ROUTER_API_BASE", "http://host.docker.internal:11434")
MODEL_NAME = "deepseek-r1:8b" 
OUTPUT_FILE = "/app/tests/data/golden_dataset.json" # Absolute path in container
SAMPLE_FILE = "/app/tests/data/sample_policy.txt"   # Absolute path in container

def load_document(filepath: str) -> str:
    """Load the sample document text."""
    with open(filepath, "r") as f:
        return f.read()

def generate_questions(context: str, mode: str) -> List[Dict]:
    """
    Generate questions using Ollama.
    mode: 'factual' or 'adversarial'
    """
    if mode == "factual":
        prompt = (
            f"Context:\n{context}\n\n"
            "Task: Generate 5 factual Question-Answer pairs that ask for specific numbers, dates, or boolean policies.\n"
            "Format: JSON list of objects with 'input', 'expected_output', and 'context' keys.\n"
            "Example: [{\"input\": \"What is X?\", \"expected_output\": \"X is Y.\", \"context\": \"Snippet...\"}]\n"
            "Strictly output only valid JSON."
        )
    else: # adversarial (graph/reasoning)
        prompt = (
            f"Context:\n{context}\n\n"
            "Task: Generate 5 adversarial Question-Answer pairs that require combining information from two different sections (e.g., 'Does Policy A contradict Policy B?').\n"
            "Format: JSON list of objects with 'input', 'expected_output', and 'context' keys.\n"
            "Strictly output only valid JSON."
        )

    print(f"🤖 Generating {mode} examples with {MODEL_NAME}...")
    
    response = requests.post(
        f"{LLM_API_BASE}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json" 
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"LLM generation failed: {response.text}")
        
    result = response.json()
    try:
        data = json.loads(result["response"])
        # Handle if the model returns a dict with a key instead of a list
        if isinstance(data, dict):
            # Try to find a list value
            for val in data.values():
                if isinstance(val, list):
                    return val
            # If no list found, wrap it
            return [data]
        return data
    except json.JSONDecodeError:
        print("❌ Failed to parse JSON response. Raw output:")
        print(result["response"])
        return []

def main():
    if not os.path.exists(SAMPLE_FILE):
        print(f"❌ Error: {SAMPLE_FILE} not found. Please run implementation plan step 1 first.")
        return

    print("📜 Loading sample document...")
    doc_text = load_document(SAMPLE_FILE)
    
    all_cases = []
    
    # Generate Factual (Vector Test)
    factual_cases = generate_questions(doc_text, "factual")
    for case in factual_cases:
        case["type"] = "factual"
    all_cases.extend(factual_cases)
    
    # Generate Adversarial (Graph Test)
    adversarial_cases = generate_questions(doc_text, "adversarial")
    for case in adversarial_cases:
        case["type"] = "thematic"
    all_cases.extend(adversarial_cases)
    
    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_cases, f, indent=2)
        
    print(f"✅ Generated {len(all_cases)} test cases in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
