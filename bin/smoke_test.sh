#!/usr/bin/env bash
set -euo pipefail

# Lab 2 smoke test: validates the full path
# Host -> NGINX -> API -> Weaviate (retrieve) -> Ollama (generate)

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env"
  exit 1
fi

EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2- | tr -d '\r')
if [ -z "$EDGE_API_KEY" ] || [ "$EDGE_API_KEY" = "change-me-to-a-long-random-string" ]; then
  echo "Set EDGE_API_KEY in .env before running tests."
  exit 1
fi

echo "[1/6] Checking proxy health..."
curl -sS http://localhost:8088/proxy-health >/dev/null
echo "  ✓ proxy-health ok"

echo "[2/6] Checking API health (auth required)..."
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health >/dev/null
echo "  ✓ /health ok"

echo "[3/6] Ingesting a test document..."
curl -sS -X POST "http://localhost:8088/ingest"   -H "Content-Type: application/json"   -H "X-API-Key: $EDGE_API_KEY"   -d '{
    "title": "Smoke Test Doc",
    "url": "https://example.com/smoke-test",
    "source": "smoke-test",
    "published_date": "2026-02-13",
    "text": "This document exists to verify that ingestion, embedding, storage, retrieval, and generation work end-to-end in Lab 2. If you can retrieve and cite this doc, your pipeline is working."
  }' >/dev/null
echo "  ✓ ingest ok"

echo "[4/6] Testing retrieval-only (debug/retrieve)..."
curl -sS -G "http://localhost:8088/debug/retrieve"   -H "X-API-Key: $EDGE_API_KEY"   --data-urlencode "q=What is this smoke test document for?" | head -c 300 >/dev/null
echo "  ✓ retrieve ok"

echo "[5/6] Testing prompt build (debug/prompt)..."
curl -sS -X POST "http://localhost:8088/debug/prompt"   -H "Content-Type: application/json"   -H "X-API-Key: $EDGE_API_KEY"   -d '{ "message": "What is this smoke test document for?" }' | head -c 300 >/dev/null
echo "  ✓ prompt ok"

echo "[6/6] Testing full chat (chat)..."
curl -sS -X POST "http://localhost:8088/chat"   -H "Content-Type: application/json"   -H "X-API-Key: $EDGE_API_KEY"   -d '{ "message": "What is this smoke test document for? Answer in 1-2 sentences." }' | head -c 300
echo ""
echo "  ✓ chat ok"

echo ""
echo "Smoke test complete."
