# Lesson 7 — RAG: Retrieval + Ollama Generation (and Debugging Each Step)

## Learning objectives

By the end of this lesson, you will be able to:

- Describe the RAG pipeline used in this lab (retrieval + generation).
- Pull and manage an Ollama model.
- Separate **retrieval problems** from **generation problems** using debug endpoints.
- Inspect the exact prompt sent to the LLM and explain how grounding works.
- Tune a simple RAG parameter (`RAG_TOP_K`) and observe how outputs change.

---

## Step 0 — Make sure you ingested data

If your database is empty, retrieval will be empty.

If you haven’t done Lesson 6, do:

```bash
./bin/ingest_sample.sh
```

---

## Step 1 — Pull an Ollama model (required)

Pull the model specified in `.env`:

```bash
./bin/pull_model.sh
```

### Beginner model advice

Start small if your machine struggles:

- `llama3.2:3b`

Set it in `.env` and pull again.

---

## Step 2 — Understand the RAG pipeline in this repo

When you hit `/chat`:

1. API calls Weaviate GraphQL with `nearText`
2. API collects top `K` docs and truncates each to a short snippet
3. API builds a prompt that includes snippets and a rule: “Use only sources”
4. API calls Ollama `/api/generate`
5. API returns answer + sources

---

## Step 3 — Debug retrieval first (no LLM)

If a student says “chat doesn’t work,” always start by proving retrieval.

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=What is defense in depth and how does this lab demonstrate it?" | python -m json.tool
```

If `sources` is empty:
- don’t touch Ollama yet
- fix ingestion/vectorizer/Weaviate first

---

## Step 4 — Inspect the prompt (this is where grounding is taught)

The `/debug/prompt` endpoint returns the exact prompt that would be sent to Ollama.

```bash
curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "Why is it risky to expose a vector database directly to the internet?" }' | python -m json.tool
```

Look for:
- “Sources:” section
- multiple `[Source 1]`, `[Source 2]` blocks
- instruction: “Use ONLY the provided sources”

### Exercise: explain grounding

In your own words, answer:
- How does the model *know* what to cite?
- What happens if sources are missing?
- Why do we return sources to the user?

---

## Step 5 — Call full chat (retrieval + generation)

```bash
curl -sS -X POST "http://localhost:8088/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "What is defense in depth and how does this lab demonstrate it? Answer in 2 sentences." }' | python -m json.tool
```

Expected:
- `answer`
- `sources` array

---

## Step 6 — Tune RAG_TOP_K and observe changes (hands-on experiment)

`RAG_TOP_K` controls how many documents are retrieved.

1) Change `.env`:
```bash
RAG_TOP_K=2
```

2) Restart only the API (so it reloads env vars):
```bash
docker compose restart ingestion-api
```

3) Call debug retrieve again and observe fewer sources:
```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=Why do we use an API layer?" | python -m json.tool
```

4) Set `RAG_TOP_K=8`, restart API, and compare.

### What you learned

- More sources can increase coverage, but may also add noise.
- Fewer sources can be focused, but might miss key context.

This is a real RAG tradeoff.

---

## Troubleshooting cheat sheet

- **Retrieval empty** → ingestion/vectorizer/Weaviate problem  
- **Retrieval works, chat fails** → Ollama/model problem  
- **Chat works but slow** → model too large or resource limits too tight  

Use logs to confirm:

```bash
docker compose logs ingestion-api --tail=200
docker compose logs ollama --tail=200
```

---

## Checkpoints (what to prove)

- You successfully pulled an Ollama model.
- `debug/retrieve` returns sources after ingestion.
- You can show the prompt from `debug/prompt` and explain grounding.
- You changed `RAG_TOP_K` and observed a measurable difference in outputs.
