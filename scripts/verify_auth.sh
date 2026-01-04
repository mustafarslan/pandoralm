
#!/bin/bash
# Verify Auth & RBAC
# Requires AUTH_BYPASS=true on Cortex or a valid token

echo "🔐 Testing Identity Mesh..."

# 1. Test Query Endpoint (Requires generic Auth)
echo "1. Testing /api/v1/query (Should success with valid token)..."
# We simulate a token by passing a dummy Bearer if Bypass is on, 
# or we need a real token. 
# Since we haven't implemented a login script, we'll rely on the Bypass Return logic 
# which triggers if the env var is set.
# BUT: The verifier checks os.getenv inside the container. 
# We need to ensure the container has AUTH_BYPASS=true or we can't test easily without a real token.
# For this verify script, let's assume we can hit it.

response=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "workspace_id": "eval-ws"}' \
  http://localhost:8000/api/v1/query)

if [ "$response" == "200" ]; then
  echo "✅ Query Auth Passed (200 OK)"
else
  echo "❌ Query Auth Failed ($response)"
fi

# 2. Test Ingest Endpoint (Requires 'vector_ops' role)
# The mock user has 'vector_ops', so this should PASS.
echo "2. Testing /api/v1/ingest/process (Should success with vector_ops)..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "workspace_id": "eval-ws"}' \
  http://localhost:8000/api/v1/ingest/process)

if [ "$response" == "202" ] || [ "$response" == "404" ]; then
  # 404 is allowed (file not found) but means Auth passed (didn't get 401/403)
  echo "✅ Ingest RBAC Passed ($response)"
else
  echo "❌ Ingest RBAC Failed ($response - Expected 202 or 404)"
fi
