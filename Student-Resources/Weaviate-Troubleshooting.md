# Lab 2 — Weaviate Troubleshooting Guide

A reference for the most common errors and issues students encounter. Find your error below and follow the fix.

---

## Table of Contents

1. [Docker & Startup Issues](#docker--startup-issues)
2. [Authentication Errors](#authentication-errors)
3. [Ingestion Errors](#ingestion-errors)
4. [Retrieval Issues](#retrieval-issues)
5. [Chat & Generation Issues](#chat--generation-issues)
6. [Security Memory Issues](#security-memory-issues)
7. [Performance Issues](#performance-issues)
8. [General Debugging Commands](#general-debugging-commands)

---

## Docker & Startup Issues

---

### Error: `Conflict. The container name "/weaviate" is already in use`

**Cause:** A container named `weaviate` is already running — usually from a previous run or another repo.

**Fix:**
```bash
docker compose down
docker rm -f weaviate
docker compose up -d --build
```

---

### Error: Port already in use (7860 or 8088)

**Cause:** Another process on your machine is using that port.

**Fix:**
```bash
# Find what's using port 8088
lsof -i :8088

# Kill it
kill -9 <PID>

# Then restart
docker compose up -d
```

---

### `text2vec-transformers` keeps restarting or shows `Exit 1`

**Cause:** The sentence-transformer model failed to download, or there isn't enough memory.

**Fix:**
```bash
docker compose logs text2vec-transformers --tail=100
```

Look for download errors. If you see memory-related errors, increase Docker Desktop memory to at least 12 GB in Docker Desktop → Settings → Resources.

---

### API health check returns `weaviate: false`

**Cause:** Weaviate hasn't finished initializing, or `text2vec-transformers` isn't healthy yet.

**Fix:** Wait 60-120 seconds after startup. Weaviate depends on `text2vec-transformers` being ready. Check both:
```bash
docker compose logs weaviate --tail=50
docker compose logs text2vec-transformers --tail=50
```

Look for confirmation that the model loaded successfully in the text2vec logs before expecting Weaviate to be healthy.

---

### UI loads at localhost:7860 but is blank or shows an error

**Cause:** Gradio started before the ingestion API was ready.

**Fix:**
```bash
docker compose restart gradio-ui
```

Wait 10 seconds then refresh the browser.

---

### `docker compose up` takes forever on first run

**Cause:** Docker is pulling all container images and `text2vec-transformers` is downloading its sentence-transformer model. Normal on first run.

**Fix:** Wait. First run can take 10-20 minutes. Subsequent runs are fast.

---

## Authentication Errors

---

### `curl` returns `401 Unauthorized`

**Cause:** The `X-API-Key` header is missing.

**Fix:**
```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health
```

---

### `curl` returns `403 Forbidden`

**Cause:** The `X-API-Key` header is present but the value is wrong.

**Fix:**
```bash
echo $EDGE_API_KEY
grep EDGE_API_KEY .env
```

If they differ, reload:
```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

---

### Changed `.env` but still getting auth errors

**Cause:** Containers loaded the old value at startup. Changes to `.env` don't take effect until restart.

**Fix:**
```bash
docker compose up -d
```

---

## Ingestion Errors

---

### `422 Unprocessable Entity` when calling `/ingest`

**Cause:** The request body failed Pydantic validation — a required field is missing or has the wrong format.

**Fix:** Check the response body for which field failed. Fix the request, not the server. This is expected behavior.

---

### `./bin/ingest_sample.sh` runs but shows no output

**Cause:** Scripts may not be executable.

**Fix:**
```bash
chmod +x bin/*.sh
./bin/ingest_sample.sh
```

---

### Ingestion fails with a Weaviate connection error

**Cause:** Weaviate isn't ready yet, or `text2vec-transformers` isn't healthy.

**Fix:**
```bash
# Check both services
docker compose ps weaviate text2vec-transformers

# Check logs
docker compose logs weaviate --tail=50
docker compose logs text2vec-transformers --tail=50
```

Wait for both to be healthy before re-running ingestion.

---

### `SchemaValidationError` or class creation fails

**Cause:** The `LabDoc` class already exists with a different schema (e.g., from a previous run without a `tags` property), and you're trying to recreate it with new properties.

**Fix:** Weaviate class schemas are immutable — you cannot modify an existing class. Delete the class and recreate:
```bash
# Wipe Weaviate data
docker compose down
docker volume rm $(docker volume ls -q | grep weaviate)
docker compose up -d --build
./bin/ingest_sample.sh
```

---

### `500 Internal Server Error` on `/ingest`

**Cause:** Usually Weaviate is not reachable from the ingestion API container, or `text2vec-transformers` went down during ingestion.

**Fix:**
```bash
# Test Weaviate reachability from inside the container
docker exec -i ingestion-api python - <<'PY'
import httpx
r = httpx.get("http://weaviate:8080/v1/meta")
print(r.status_code, r.text[:200])
PY

docker compose logs weaviate --tail=50
docker compose logs text2vec-transformers --tail=50
```

---

## Retrieval Issues

---

### `/debug/retrieve` returns an empty `sources` array

**Cause (most common):** Nothing has been ingested yet.

**Fix:**
```bash
./bin/ingest_sample.sh
```

**Other causes:**
- `text2vec-transformers` was down during ingestion — embeddings weren't generated, so objects aren't searchable. Re-ingest after confirming text2vec is healthy.
- Query doesn't match the dataset — try `"CIA triad"` or `"defense in depth"`.
- Weaviate isn't ready — check `docker compose logs weaviate`.

---

### Retrieval returns results but they look completely unrelated

**Cause:** The embedding model may not have loaded correctly during ingestion.

**Fix:**
```bash
# Confirm text2vec is healthy
docker compose logs text2vec-transformers --tail=30

# Wipe and re-ingest
./bin/reset_all.sh
docker compose up -d --build
./bin/pull_model.sh
./bin/ingest_sample.sh
```

---

### Distance scores are all very high (above 1.0)

**Cause:** In Weaviate, distance scores close to 0 are excellent and scores above 1.0 are poor matches. High scores mean the query doesn't match the content well.

**⚠ Important reminder:** Weaviate uses DISTANCE (lower = better). This is the opposite of Qdrant which uses SIMILARITY (higher = better). A distance of 0.12 is an excellent match. A distance of 1.4 is a poor match.

**Fix:** Rephrase the query to more closely match the language in your ingested documents.

---

### I see results but `distance=0.89` — is that good or bad?

**Answer:** In Weaviate, distance 0.89 is a mediocre match. Here is the reference scale:

| Distance | Quality |
|---|---|
| Below 0.2 | Excellent |
| 0.2 – 0.5 | Good |
| 0.5 – 1.0 | Acceptable |
| Above 1.0 | Poor |

---

## Chat & Generation Issues

---

### `/chat` returns `{"detail": "Chat timed out."}`

**Cause:** Ollama is taking too long to generate.

**Fix:**
```bash
# Confirm model exists
docker exec -it ollama ollama list

# If missing, pull it
./bin/pull_model.sh

# Increase timeout in .env
CHAT_TOTAL_TIMEOUT_S=300
OLLAMA_TIMEOUT_S=240

docker compose restart ingestion-api
```

---

### `/chat` hangs indefinitely

**Cause:** Ollama is running but the model hasn't been pulled, or Ollama ran out of memory.

**Fix:**
```bash
docker compose logs ollama --tail=50
docker exec -it ollama ollama list
./bin/pull_model.sh
```

---

### Chat answers reference `example.org` sources

**Cause:** This is expected — the sample dataset (`data/sample_articles.jsonl`) uses `example.org` placeholder URLs. The security memory corpus (NIST, CIS, OWASP) is separate and injected silently into the prompt when security questions are detected. The sources shown in chat are from the main `LabDoc` class only.

**Fix:** This is not a bug. To test security memory retrieval directly use `/memory/query` from the terminal or the Security Memory tab in Gradio.

---

### Chat answers are vague and don't cite specific standards

**Cause:** Either the security memory module isn't loaded, or the model is too small.

**Fix:**
```bash
# Confirm memory health
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s http://localhost:8088/memory/health -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool

# If ok: false, copy the patches module
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api

# For better answers, use a larger model in .env
OLLAMA_MODEL=llama3.2:3b
docker compose restart ingestion-api
```

---

## Security Memory Issues

---

### `ModuleNotFoundError: No module named 'app.security_memory'`

**Cause:** The security memory module hasn't been copied into the container. In the Weaviate lab, this module lives in `patches/` and must be applied with `docker cp` — it is NOT baked into the Docker image automatically.

**Fix:**
```bash
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api
```

⚠ **Important:** You must repeat this copy after every `docker compose up --build` or container recreate. The copy does not survive rebuilds.

---

### `/memory/health` returns `{"detail": "Not Found"}` after copying the module

**Cause:** FastAPI loaded before the files were copied, so the router wasn't registered at startup.

**Fix:** Always restart after copying:
```bash
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api
```

Wait 10 seconds, then test again.

---

### `/memory/health` returns `{"detail": "Not Found"}` after a restart

**Cause:** The restart wiped the copied files because they weren't in the Docker image. You need to copy again.

**Fix:** This is the standard Weaviate workflow — copy then restart every time:
```bash
docker compose up -d --build ingestion-api
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api
```

---

### `SECURITY_DATA_DIR not found: /securitymemory/data`

**Cause:** The volume mount is missing from `docker-compose.yml` or `security-memory/data/` is empty.

**Fix:**
```bash
# Check files exist locally
ls security-memory/data/

# Check container can see them
docker exec -i ingestion-api ls /securitymemory/data

# If missing in container, confirm this is in docker-compose.yml under ingestion-api volumes:
# - ./security-memory/data:/securitymemory/data:ro

docker compose up -d --force-recreate ingestion-api
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api
```

---

### Security memory ingestion returns empty results from `/memory/query`

**Cause:** Ingestion ran but vectors weren't stored, or the class wasn't created.

**Fix:**
```bash
# Check count via GraphQL
docker exec -i ingestion-api python - <<'PY'
import httpx, os
r = httpx.post(
    f"http://{os.getenv('WEAVIATE_HOST','weaviate')}:{os.getenv('WEAVIATE_PORT','8080')}/v1/graphql",
    json={"query": "{ Aggregate { ExpandedVSCodeMemory { meta { count } } } }"}
)
print(r.json())
PY
```

If count is 0, re-run ingestion:
```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

---

### Security memory ingestion is taking a very long time

**Cause:** Normal — large corpus with many Ollama embedding calls.

**Fix:** Don't cancel it. Monitor:
```bash
docker stats          # Watch Ollama CPU — should be high
docker logs -f ingestion-api  # Watch progress
```

---

## Performance Issues

---

### Everything is slow — fan running constantly

**Cause:** Docker Desktop doesn't have enough memory, or both Weaviate and text2vec-transformers are competing for RAM.

**Fix:**
1. Open Docker Desktop → Settings → Resources → increase Memory to at least 12 GB
2. Or reduce limits in `docker-compose.yml`:
```yaml
mem_limit: 4g
```

Restart after changes:
```bash
docker compose down
docker compose up -d
```

---

### `text2vec-transformers` is using a lot of memory

**Cause:** The sentence-transformer model is loaded into memory and stays there. This is normal.

**Fix:** If memory is tight, reduce the `mem_limit` for `text2vec-transformers` cautiously — too low and it will crash. 1-2 GB is usually sufficient.

---

## General Debugging Commands

Use these any time something isn't working:

```bash
# See status of all containers
docker compose ps

# See resource usage (CPU + memory) per container
docker stats

# View logs for a specific service
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
docker compose logs ingestion-api --tail=200
docker compose logs ollama --tail=200
docker compose logs nginx --tail=200

# Follow logs in real time
docker compose logs -f ingestion-api

# Run the smoke test
./bin/smoke_test.sh

# Check proxy health (no auth required)
curl -i http://localhost:8088/proxy-health

# Check API health (auth required)
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health

# Test retrieval only (no LLM)
curl -sS -G http://localhost:8088/debug/retrieve \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=CIA triad" | python -m json.tool

# Check Weaviate object count
docker exec -i ingestion-api python - <<'PY'
import httpx
r = httpx.post("http://weaviate:8080/v1/graphql",
    json={"query": "{ Aggregate { LabDoc { meta { count } } } }"})
print(r.json())
PY

# Copy security memory module (must redo after every rebuild)
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api

# Full reset (deletes all data and models)
./bin/reset_all.sh
```
