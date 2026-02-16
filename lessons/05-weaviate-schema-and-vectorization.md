# Lesson 5 — Weaviate Schema & Vectorization (Guided Schema Build)

## Learning objectives

By the end of this lesson, you will be able to:

- Explain what a Weaviate schema is and why it exists.
- Explain embeddings in beginner language.
- Verify Weaviate and the vectorizer are healthy from inside Docker.
- Make a small schema change (add a new field), rebuild, and prove ingestion still works.

---

## Step 1 — Beginner mental model

Weaviate stores:

- **objects** (your documents)
- **vectors** (numeric embeddings representing meaning)

The vectorizer service turns `text` into vectors so Weaviate can do semantic search.

---

## Step 2 — Verify readiness (internal-only testing)

We do not expose Weaviate to the host.
So we test from inside a container on the internal Docker network.

### 2.1 Weaviate ready?

```bash
docker exec -it ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://weaviate:8080/v1/.well-known/ready").read().decode())
PY
```

### 2.2 Vectorizer ready?

```bash
docker exec -it ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://text2vec-transformers:8080/.well-known/ready").read().decode())
PY
```

If either fails, check logs:

```bash
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
```

---

## Step 3 — Guided build: add a new schema field (`tags`)

Real datasets often include metadata.
We’ll add a simple list field called `tags`.

### 3.1 Update the request schema

Open:

- `ingestion-api/app/schemas.py`

Add `tags` to `ArticleIn`:

- Type: `list[str]`
- Optional: default empty list

Example:

```python
from typing import List

tags: List[str] = []
```

(Place it inside the `ArticleIn` class.)

### 3.2 Update schema creation

Open:

- `ingestion-api/app/weaviate_client.py`

Find the schema for class `LabDoc`.
Add a new property:

- name: `tags`
- dataType: `text[]`

(That means “array of strings.”)

### 3.3 Update sample data (optional)

Open:

- `data/sample_articles.jsonl`

Add `"tags": ["lab2", "security"]` to a couple of lines.

---

## Step 4 — Rebuild and re-run ingestion

Rebuild API:

```bash
docker compose up -d --build ingestion-api
```

Ingest one doc with tags:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Tagged Doc",
    "url": "https://example.com/tagged",
    "source": "Manual",
    "published_date": "2026-02-13",
    "tags": ["lab2", "schema-change"],
    "text": "This document proves schema changes can be applied safely through the API layer and that ingestion still works."
  }'
```

---

## Step 5 — Prove retrieval still works

```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=schema changes applied safely" | python -m json.tool
```

---

## Checkpoints (what to prove)

- You verified Weaviate and vectorizer readiness.
- You added the `tags` field (schema + request model).
- You ingested a document containing tags successfully.
- Retrieval still returns sources.
