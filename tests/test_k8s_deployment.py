import requests
import time
import pytest

# Configuration (match bootstrap.sh)
BASE_URL = "http://localhost" # Mapped by Kind ports 80/443
CORTEX_HEALTH_URL = f"{BASE_URL}/api/health" # Ingress routes /api -> cortex
CORE_URL = f"{BASE_URL}/"

def test_deployment_health():
    """Verify that the PandoraLM stack is up and responding."""
    
    # 1. Check Core (Frontend)
    print(f"Checking Core at {CORE_URL}...")
    # Might need retry logic if startup is slow
    retries = 5
    for i in range(retries):
        try:
            response = requests.get(CORE_URL, timeout=5)
            if response.status_code < 500: # 200 or 404 is 'responsive' compared to connection error
                print("✅ Core is responsive")
                break
        except requests.exceptions.ConnectionError:
            print(f"Waiting for Core... ({i+1}/{retries})")
            time.sleep(5)
    else:
        pytest.fail("Core service is not reachable via Ingress")

    # 2. Check Cortex (Backend)
    print(f"Checking Cortex at {CORTEX_HEALTH_URL}...")
    try:
        # Note: Ingress routing /api -> cortex port 8000
        # Cortex health is /api/v1/health or /health dependent on router.
        # Deployment check says livenessProbe: httpGet: path: /health
        # But Ingress routes /api -> cortex. 
        # If cortex mounts at /, then /api/health -> cortex/health
        
        # Let's try both common paths
        paths = ["/api/health", "/api/v1/health"]
        success = False
        for path in paths:
            url = f"{BASE_URL}{path}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Cortex is healthy at {path}")
                success = True
                break
        
        if not success:
             pytest.fail(f"Cortex health check failed. Tried {paths}")

    except Exception as e:
        pytest.fail(f"Cortex unreachable: {e}")

if __name__ == "__main__":
    test_deployment_health()
