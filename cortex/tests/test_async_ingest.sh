#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"
FILENAME="async_test.txt"

echo "🚀 Starting Async Ingestion Test (Shell)..."

# 1. Trigger Ingestion
echo "📡 Sending request to $BASE_URL/ingest/process..."
RESPONSE=$(curl -s -X POST "$BASE_URL/ingest/process" \
  -H "Content-Type: application/json" \
  -d "{\"filename\": \"$FILENAME\", \"workspace_id\": \"test-workspace\", \"trigger_graph_indexing\": true}")

JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
DOC_ID=$(echo $RESPONSE | grep -o '"document_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$DOC_ID" ]; then
  echo "❌ Failed to trigger ingestion. Response: $RESPONSE"
  exit 1
fi

echo "✅ Accepted! Document ID: $DOC_ID, Job ID: $JOB_ID"

# 2. Poll Status
echo "⏳ Polling status for $DOC_ID..."
MAX_WAIT=60
START_TIME=$(date +%s)

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  if [ $ELAPSED -gt $MAX_WAIT ]; then
    echo "❌ Timeout waiting for vector completion."
    exit 1
  fi
  
  STATUS_RES=$(curl -s "$BASE_URL/document/$DOC_ID/status")
  VECTOR_STATUS=$(echo $STATUS_RES | grep -o '"vector_status":"[^"]*"' | cut -d'"' -f4)
  GRAPH_STATUS=$(echo $STATUS_RES | grep -o '"graph_status":"[^"]*"' | cut -d'"' -f4)
  VECTOR_PROG=$(echo $STATUS_RES | grep -o '"vector_progress":[^,]*' | cut -d':' -f2 | cut -d',' -f1)
  
  echo "   [$ELAPSED s] Status: Vector=$VECTOR_STATUS ($VECTOR_PROG), Graph=$GRAPH_STATUS"
  
  if [ "$VECTOR_STATUS" == "completed" ]; then
    echo "✨ Fast Lane Complete! Vector Search Ready."
    echo "✅ Test Passed: Async flow works."
    exit 0
  fi
  
  if [ "$VECTOR_STATUS" == "failed" ]; then
    MESSAGE=$(echo $STATUS_RES | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    echo "❌ Vectorization Failed: $MESSAGE"
    exit 1
  fi
  
  sleep 2
done
