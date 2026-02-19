# Lesson 9 — Operations: Runbooks, Failure Drills, and Debugging 

## Learning objectives

By the end of this lesson, you will be able to:

- Use health endpoints to confirm the system is ready.
- Use logs to debug issues across multiple containers.
- Perform multiple failure drills and write a short “incident note” for each.
- Use the smoke test as a repeatable proof of system health.
- Reset the lab safely and explain what data is deleted.

Much of this lesson is a refresher over commands and debugging techniques used throughout this repo. This lesson provides a good base for future knowledge and endeavors in working with RAG chatbots and Weaviate.

---

## Step 1 — Health endpoints (fast checks)

### Proxy health (no auth)

```bash
curl -i http://localhost:8088/proxy-health
```

If this fails:
- NGINX is down
- or Docker ports are not mapped correctly

### API health (auth required)

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health
```

If this fails:
- auth is wrong (401/403)
- or API can’t reach Weaviate
- check logs for root cause

---

## Step 2 — Logs (the #1 debugging tool)

### Follow logs for all services

```bash
./bin/logs.sh
```

### Target one service

```bash
docker compose logs ingestion-api --tail=200
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
docker compose logs ollama --tail=200
docker compose logs nginx --tail=200
```

### Beginner rule

If you don’t know what’s wrong yet:
1) check `docker compose ps`
2) check logs
3) check health endpoints

Do not guess.

---

## Step 3 — Smoke test (your “it works” button)

Run:

```bash
./bin/smoke_test.sh
```

This confirms:
- proxy
- auth
- ingest
- retrieval
- prompt build
- chat generation

If a TA asks “does it work,” this is the proof.

---

## Step 4 — Failure drills (operations practice)

Each drill has the same structure:

1) Run smoke test (baseline)
2) Break one component
3) Observe symptoms (health + UI)
4) Identify cause using logs
5) Fix it
6) Run smoke test again

### Drill A — Stop Ollama (generation fails)

```bash
docker stop ollama
```

Expected:
- `debug/retrieve` still works
- `/chat` fails (generation step)
- logs show connection failure to Ollama

Fix:

```bash
docker start ollama
```

### Drill B — Stop Weaviate (retrieval fails)

```bash
docker stop weaviate
```

Expected:
- `/health` may report `ok: false`
- `debug/retrieve` fails
- chat fails (because retrieval step fails)

Fix:

```bash
docker start weaviate
```

### Drill C — Stop text2vec-transformers (ingest still may succeed, but vectors break)

```bash
docker stop text2vec-transformers
```

Now try ingesting a new doc:
- you may see errors on ingest
- or retrieval becomes worse because embeddings can’t be produced

Fix:

```bash
docker start text2vec-transformers
```

---

## Step 6 — Reset vs stop (don’t accidentally delete your work)

Stop containers (keeps data/models):

```bash
docker compose down
```

Full wipe (deletes Weaviate data + Ollama models):

```bash
./bin/reset_all.sh
```

---

## Extra: Useful Docker commands for beginners

- See running services:
  ```bash
  docker compose ps
  ```
- Restart a service:
  ```bash
  docker compose restart ingestion-api
  ```
- Rebuild after code changes:
  ```bash
  docker compose up -d --build
  ```
- Resource usage:
  ```bash
  docker stats
  ```

---

## Checkpoints 
- You can explain the dependency chain (UI → proxy → API → Weaviate/Ollama).
- You can reset the lab and explain exactly what was deleted.
