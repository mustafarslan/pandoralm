
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_async_flow():
    print("🚀 Starting Async Ingestion Test...")
    
    # 1. Trigger Ingestion
    payload = {
        "filename": "async_test.txt",
        "workspace_id": "test-workspace",
        "trigger_graph_indexing": True
    }
    
    print(f"📡 Sending request to {BASE_URL}/ingest/process...")
    try:
        response = requests.post(f"{BASE_URL}/ingest/process", json=payload)
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Is it running?")
        sys.exit(1)
        
    if response.status_code != 202:
        print(f"❌ Failed to trigger ingestion: {response.status_code} - {response.text}")
        sys.exit(1)
        
    data = response.json()
    doc_id = data["document_id"]
    job_id = data["job_id"]
    print(f"✅ Accepted! Document ID: {doc_id}, Job ID: {job_id}")
    
    # 2. Poll Status
    print(f"⏳ Polling status for {doc_id}...")
    start_time = time.time()
    max_wait = 60 # wait up to 60 seconds
    
    while time.time() - start_time < max_wait:
        status_res = requests.get(f"{BASE_URL}/document/{doc_id}/status")
        if status_res.status_code != 200:
            print(f"⚠️ Status check failed: {status_res.status_code}")
            time.sleep(1)
            continue
            
        status = status_res.json()
        v_status = status["vector_status"]
        g_status = status["graph_status"]
        v_prog = status["vector_progress"]
        
        print(f"   Status: Vector={v_status} ({v_prog:.1f}), Graph={g_status}")
        
        if v_status == "completed":
            print("✨ Fast Lane Complete! Vector Search Ready.")
            
            # Since this is a tiny file, graph might also finish quickly or be in progress
            if g_status in ["processing", "completed"]:
                print("✅ Test Passed: Async flow works.")
                return
        
        if v_status == "failed":
            print(f"❌ Vectorization Failed: {status.get('message')}")
            sys.exit(1)
            
        time.sleep(1)
        
    print("❌ Timeout waiting for vector completion.")
    sys.exit(1)

if __name__ == "__main__":
    test_async_flow()
