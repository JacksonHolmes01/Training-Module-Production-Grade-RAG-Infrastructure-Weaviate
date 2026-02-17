# Lesson 6 — Ingestion API: Validation, Ingest, and Proving It Works

## Learning objectives

By the end of this lesson, you will be able to:

- Explain why ingestion should happen through an API (not directly to the DB).
- Use `curl` to ingest documents through **NGINX → API → Weaviate**.
- Trigger and interpret validation errors (422) on purpose.
- Verify ingestion by performing a **retrieval-only** query (no LLM).
- Run a repeatable smoke test that demonstrates end-to-end functionality.

---

## Mental model (what you are building)

When you ingest a document, the system does multiple steps:

1. **NGINX** checks API key
2. **FastAPI** validates the JSON request body
3. **Weaviate** stores the object
4. **Vectorizer module** generates embeddings so the object becomes retrievable by meaning

If any one of these steps fails, ingestion may appear to work but retrieval will be broken.

So in this lesson we will **prove** each part works.

---

## Step 1 — Why an ingestion API exists (beginner explanation)

If you expose your database directly:

- anyone can send junk data
- you can’t enforce consistent rules easily
- you lose a clean place to log and audit
- you increase attack surface

An ingestion API gives you a **control point**:

- validate input shape (required fields, types)
- reject bad requests early
- enforce authentication consistently
- later: add chunking, deduplication, rate limiting, logging

This is why production systems typically have an API layer.

---

## Step 2 — Learn the endpoints we will use

Through the NGINX proxy you can access:

- `GET  http://localhost:8088/proxy-health` (no auth)
- `GET  http://localhost:8088/health` (auth)
- `POST http://localhost:8088/ingest` (auth)
- `POST http://localhost:8088/chat` (auth)
- `GET  http://localhost:8088/debug/retrieve?q=...` (auth)  ✅ retrieval test
- `POST http://localhost:8088/debug/prompt` (auth)          ✅ prompt inspection

Those `/debug/*` endpoints are teaching tools: they help you separate retrieval issues from generation issues.

---

## Step 3 — Load your API key into your shell

From the repo root:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
echo "$EDGE_API_KEY" | wc -c
```

You should see a length much larger than 20 characters.

---

## Step 4 — Ingest one document by hand (curl)

Send a valid request:

```bash
curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Test Doc",
    "url": "https://example.com/test",
    "source": "Manual",
    "published_date": "2026-02-12",
    "text": "This is a test document with enough text to pass validation. It exists to verify the ingest pipeline works end to end."
  }'
```

### Expected result

- HTTP `200`
- JSON response with a Weaviate object id

If you get 401/403 → go back to Lesson 4 (auth).  
If you get 500 → check logs (`docker compose logs ingestion-api --tail=200`).

---

## Step 5 — Trigger a validation error on purpose (learning exercise)

Validation errors are **good**: they mean your API is protecting the database.

Try ingesting with a bad URL:

```bash
curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Bad Doc",
    "url": "not-a-real-url",
    "source": "Manual",
    "published_date": "2026-02-12",
    "text": "This text is long enough, but the URL is invalid, so validation should fail."
  }'
```

Expected:
- HTTP `422 Unprocessable Entity`

---

## Step 6 — Ingest the sample dataset (recommended)

This repo includes:

- `data/sample_articles.jsonl`

Run:

```bash
./bin/ingest_sample.sh
```

You should see multiple “Documnet Ingested” lines.

---

## Step 7 — Verify ingestion using retrieval-only (NO LLM)

This is the most important “proof” step for beginners.

If retrieval works, your database + vectorizer are good.

Run:

```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=Why is exposing databases directly to the internet risky?" | python -m json.tool
```

Look for:
- a `sources` array
- titles and URLs from your ingested docs

If `sources` is empty:
- ingestion may have failed
- vectorizer may be down
- Weaviate may not be ready yet

Check:
```bash
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python -m json.tool
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
```

---

## Step 8 — Run the smoke test 

This repo includes a smoke test script that demonstrates:

- proxy works
- auth works
- ingest works
- retrieval works
- prompt build works
- chat works (may take longer than the others)

Run:

```bash
./bin/smoke_test.sh
```

If it passes, you have strong evidence the system is working.

---

## If `chat` Hangs or Times Out

The `/chat` endpoint is the slowest operation because it performs multiple steps:

1. Retrieval from Weaviate  
2. Prompt construction  
3. Local LLM generation via Ollama  

If `chat` appears to hang, isolate the failing stage using the debug endpoints below.

---

### 1. Verify Retrieval Works (Fast)

```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=CIA triad" | python -m json.tool
```

If this fails, check:

```bash
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
```

---

### 2. Verify Prompt Construction Works

```bash
curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the CIA triad?"}' | python -m json.tool
```

If this fails, your retrieval layer or prompt builder has an issue.

---

### 3. Test Ollama Directly (Generation Only)

```bash
curl -sS -X POST "http://localhost:8088/debug/ollama" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain the CIA triad in 2 sentences."}' | python -m json.tool
```

If this hangs:

- Your model may be too large for available RAM  
- The model may not be pulled  
- Ollama may be restarting  

Check:

```bash
docker compose logs ollama --tail=200
docker exec -it ollama ollama list
```

---

### 4. Check API Logs

```bash
docker compose logs ingestion-api --tail=200
```

Look for:
- Timeouts  
- NameErrors  
- Connection errors  
- 500 responses  

---

### 5. Common Causes of Slow Chat

- Large model (e.g., 8B) on limited RAM  
- Extremely long prompts  
- Too many retrieved documents  
- Insufficient Docker memory allocation  

If retrieval and prompt work but generation is slow, the issue is almost always model size or available memory.

---

## Checkpoints 

- You can ingest one document with curl and get `200`.
- You can intentionally trigger a `422` validation error and explain it.
- `debug/retrieve` returns at least 1 source after ingestion.
- `./bin/smoke_test.sh` completes successfully.

[Lesson 7](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/07-rag-retrieval-and-ollama.md)
