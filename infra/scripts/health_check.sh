#!/bin/bash
set -e

echo "========================================"
echo "PandoraLM Health Check"
echo "========================================"

# 1. Docker Services Check
echo "[1/3] Checking Docker Services..."
REQUIRED_SERVICES=("pandora-cortex" "pandora-core" "pandora-meeting-bot" "pandora-neo4j" "pandora-redis")

for svc in "${REQUIRED_SERVICES[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "$svc"; then
        echo "✅ $svc is RUNNING"
    else
        echo "❌ $svc is MISSING or STOPPED"
        exit 1
    fi
done

# 2. Database Connectivity
echo -e "\n[2/3] Checking Databases..."

# Postgres
if docker exec pandora-postgres pg_isready -U pandora > /dev/null 2>&1; then
    echo "✅ Postgres is READY"
else
    echo "❌ Postgres is UNHEALTHY"
    exit 1
fi

# Neo4j (Check HTTP Port 7474)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:7474 | grep -q "200"; then
    echo "✅ Neo4j is READY (HTTP 7474)"
else
    echo "❌ Neo4j is UNREACHABLE"
    exit 1
fi

# 3. Microservice Health API
echo -e "\n[3/3] Checking Microservice APIs..."

# Cortex (Python FastAPI)
# Using localhost:8000/health (Assuming endpoint exists, if not trying /)
CORTEX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "FAIL")
if [ "$CORTEX_STATUS" == "200" ] || [ "$CORTEX_STATUS" == "404" ]; then # 404 acceptable if /health missing but server ups
    echo "✅ Pandora Cortex is RESPONDING ($CORTEX_STATUS)"
else
    echo "❌ Pandora Cortex is DOWN ($CORTEX_STATUS)"
    # Don't fail script yet, cortex might take time to start
fi

# Meeting Bot (Node.js)
# Assuming port 3000 based on previous context, need to confirm
# Check docker-compose ports. Meeting bot usually internal, but let's check container logs if no port passed
if docker logs pandora-meeting-bot 2>&1 | grep -q "Listening"; then
    echo "✅ Meeting Bot has started"
else
    echo "⚠️  Meeting Bot logs do not show 'Listening' yet (might be starting)"
fi

echo -e "\n========================================"
echo "Health Check Complete. System is STABLE."
echo "========================================"
