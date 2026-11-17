#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env"
  exit 1
fi

MODEL=$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2- | tr -d '\r')
if [ -z "$MODEL" ]; then
  echo "OLLAMA_MODEL not set in .env"
  exit 1
fi

echo "Pulling Ollama model: $MODEL"
docker exec -it ollama ollama pull "$MODEL"
echo "Done."
