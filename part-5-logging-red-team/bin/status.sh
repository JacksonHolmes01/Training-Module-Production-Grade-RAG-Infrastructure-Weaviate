#!/usr/bin/env bash
cd "$(dirname "$0")/.."
docker compose ps
echo; docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' rag-weaviate rag-ollama rag-api rag-nginx rag-ui 2>/dev/null
