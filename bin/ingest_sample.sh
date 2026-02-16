#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env"
  exit 1
fi

EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2- | tr -d '\r')
if [ -z "$EDGE_API_KEY" ] || [ "$EDGE_API_KEY" = "change-me-to-a-long-random-string" ]; then
  echo "Set EDGE_API_KEY in .env before ingesting."
  exit 1
fi

FILE="data/sample_articles.jsonl"
if [ ! -f "$FILE" ]; then
  echo "Missing $FILE"
  exit 1
fi

echo "Ingesting sample docs into Weaviate via the edge proxy..."
while IFS= read -r line; do
  [ -z "$line" ] && continue
  curl -sS -X POST "http://localhost:8088/ingest" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $EDGE_API_KEY" \
    -d "$line" > /dev/null
  echo "  ✓ ingested one doc"
done < "$FILE"

echo "Done."
