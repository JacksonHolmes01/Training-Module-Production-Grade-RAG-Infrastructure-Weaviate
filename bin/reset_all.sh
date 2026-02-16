#!/usr/bin/env bash
set -euo pipefail
echo "Stopping containers..."
docker compose down
echo "Removing volumes (THIS DELETES WEAVIATE DATA + OLLAMA MODELS)..."
docker volume rm -f $(docker volume ls -q | grep -E 'weaviate_data|ollama_data' || true) 2>/dev/null || true
echo "Done."
