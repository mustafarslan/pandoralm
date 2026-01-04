import requests
import time
import subprocess
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import redis
import json

# Config
MOCK_SERVER_PORT = 8888
BOT_API_URL = "http://localhost:3002/join"
FIXTURE_PATH = "tests/fixtures/mock_meeting.html"

def start_mock_server():
    """Starts a simple HTTP server to serve the fixture"""
    print(f"[Test] Starting mock server on port {MOCK_SERVER_PORT}...")
    server_address = ('', MOCK_SERVER_PORT)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

def verify_flow():
    # 1. Start Server in Thread
    server_thread = threading.Thread(target=start_mock_server, daemon=True)
    server_thread.start()
    
    # Allow server to startup
    time.sleep(2)
    
    # 2. Construct usage URL (using host.docker.internal if assumed docker networking, 
    # but for local process testing we use localhost)
    
    # CHECK: Is the bot running?
    try:
        # Assuming user is running `npm run dev` in services/meeting-bot or via docker
        # If we want to fully E2E this script, we should probably start the bot subprocess too
        # But usually E2E assumes environment is up. 
        # For this script we will assume the bot is listening on 3002.
        pass
    except Exception:
        print("[Test] Bot service not found on port 3002. Please start it.")
        return

    # Use host.docker.internal if bot is in docker, else localhost
    # Since we are likely testing locally first:
    target_url = f"http://host.docker.internal:{MOCK_SERVER_PORT}/{FIXTURE_PATH}"
    # Fallback for local
    # target_url = f"http://localhost:{MOCK_SERVER_PORT}/{FIXTURE_PATH}"

    print(f"[Test] Instructing bot to join: {target_url}")
    
    payload = {
        "url": target_url,
        "layer_id": "test_layer",
        "meeting_meta": {
            "title": "E2E Verification",
            "duration": 5
        }
    }
    
    try:
        res = requests.post(BOT_API_URL, json=payload)
        print(f"[Test] Bot Response: {res.status_code} - {res.text}")
        
        if res.status_code == 202:
            print("[Test] SUCCESS: Bot accepted the job.")
            print("[Test] Waiting 60 seconds for stream to complete (slow emulation)...")
            time.sleep(60)
            
            # Check Redis
            try:
                r = redis.Redis(host='localhost', port=6379, db=0)
                # Check list
                item = r.lpop('audio_processing_queue')
                if item:
                    print(f"[Test] SUCCESS: Found job in Redis: {item}")
                else:
                    print("[Test] FAILURE: Redis queue empty after 10s.")
            except Exception as e:
                print(f"[Test] WARNING: Could not connect to local Redis to verify: {e}")

        else:
            print("[Test] FAILED: Bot rejected the job.")
            
    except Exception as e:
        print(f"[Test] Failed to contact bot: {e}")
        print("Make sure 'npm run dev' is running in services/meeting-bot")

if __name__ == "__main__":
    # Ensure fixture exists
    if not os.path.exists(FIXTURE_PATH):
        print(f"Fixture not found at {FIXTURE_PATH}")
        # Create dummy if missing (though we created it via tool)
        os.makedirs("tests/fixtures", exist_ok=True)
        with open(FIXTURE_PATH, "w") as f:
            f.write("<html><body><h1>Mock</h1></body></html>")
            
    verify_flow()
