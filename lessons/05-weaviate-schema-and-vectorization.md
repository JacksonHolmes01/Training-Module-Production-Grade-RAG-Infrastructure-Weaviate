# Lesson 5 — Weaviate Schema & Vectorization  


---

## Learning Objectives

By the end of this lesson, you will be able to:

- Explain what a **Weaviate schema** is and why it exists.
- Explain **embeddings** in beginner-friendly language.
- Verify Weaviate and the vectorizer are healthy from inside Docker.
- Safely extend a schema with a new field.
- Rebuild and validate ingestion without breaking retrieval.
- Understand why schema changes must be controlled in production systems.

---

# Step 1 — Mental Model: What’s Actually Happening

Weaviate stores two things:

- **Objects** → Your structured documents (JSON)
- **Vectors** → Numeric embeddings representing semantic meaning

The vectorizer service (`text2vec-transformers`) converts your `text` field into a vector automatically.

That vector enables **semantic search**.

Instead of matching keywords, Weaviate retrieves documents based on meaning.

System flow:

User → Edge (NGINX) → Ingestion API → Weaviate  
                                      ↳ Vectorizer (embeddings)

---

# Step 2 — Verify Internal Readiness

We do NOT expose Weaviate to localhost.  
Everything runs inside Docker’s internal network.

---

## 2.1 Check Weaviate Readiness

```bash
docker exec -i ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://weaviate:8080/v1/.well-known/ready").read().decode())
PY
```

### Expected Output

```text
OK
```

---

## 2.2 Check Vectorizer Readiness

```bash
docker exec -i ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://text2vec-transformers:8080/.well-known/ready").read().decode())
PY
```

### Expected Output

```text
```

(Vectorizer returns HTTP 204 — no body — which is normal.)

If either fails:

```bash
docker compose logs weaviate --tail=200
docker compose logs text2vec-transformers --tail=200
```

---

# Step 3 — Guided Schema Change: Add `tags`

Real-world datasets need metadata for:

- Filtering
- Categorization
- Governance
- Analytics

We will extend the system safely.

---

# Step 3.1 — Update the API Request Model (`schemas.py`)

In this step, you will update the FastAPI request model so the API is allowed to accept a new `tags` field.

Remember:

Your **API schema** defines what data is valid.  
If you do not update this file, ingestion will reject requests containing `tags`.

---

## Open the File

You need to open:

```
ingestion-api/app/schemas.py
```

You can do this in two different ways.

---

## Option A — Using a Code Editor (VS Code, Cursor, etc.)

1. Open your project folder.
2. Navigate through the sidebar:

   ```
   ingestion-api
     └── app
         └── schemas.py
   ```

3. Click on `schemas.py` to open it.
4. Find the class:

   ```python
   class ArticleIn(BaseModel):
   ```

---

## Option B — Using the Terminal (Nano)

From the root of your project directory, run:

```bash
nano ingestion-api/app/schemas.py
```

Navigation tips:

- Use arrow keys to move the cursor.
- Press `Ctrl + O` to save.
- Press `Enter` to confirm.
- Press `Ctrl + X` to exit.

---

## Make the Change

Update the `ArticleIn` model to include the `tags` field.

Your updated class should look like this:

```python
from typing import List
from pydantic import BaseModel

class ArticleIn(BaseModel):
    title: str
    url: str
    source: str
    published_date: str
    text: str
    tags: List[str] = []
```

---

## Why This Matters

- `List[str]` means this field accepts an array of strings.
- The default `[]` prevents validation errors if tags are not provided.
- The API model must stay aligned with the database schema.
- If these drift apart, ingestion will fail.

---

## What You Just Did

You extended the **API contract**.

Before:
- The API rejected any `tags` field.

After:
- The API now validates and accepts `tags` safely.

This is the first step in a safe schema migration.

# Step 3.2 — Update the Database Schema (`weaviate_client.py`)

Open:

```
ingestion-api/app/weaviate_client.py
```

You can open this file in two ways:

### Option A — Using a Code Editor (VS Code, Cursor, etc.)

1. Open your project folder.
2. Navigate to:

   ```
   ingestion-api/app/
   ```

3. Click on:

   ```
   weaviate_client.py
   ```

4. Scroll to the `ensure_schema()` function.
5. Locate the `properties` list.

---

### Option B — Using the Terminal (Nano)

From the root of your project directory, run:

```bash
nano ingestion-api/app/weaviate_client.py
```

- Use arrow keys to navigate.
- Make your changes.
- Press `Ctrl + O` to save.
- Press `Enter`.
- Press `Ctrl + X` to exit.

---

Inside the `properties` list in `ensure_schema()`, add:

```python
{
    "name": "tags",
    "dataType": ["text[]"],
    "description": "Metadata tags for the article"
}
```

Important:

- `text[]` means array of strings.
- Schema types must match your ingestion model exactly.
- API model and DB schema must stay aligned.

Save the file.

---


# Step 3.3 — Update Sample Data

Open:

```
data/sample_articles.jsonl
```

Modify one line to include tags:

```json
{"title": "Example", "url": "https://example.com", "source": "Manual", "published_date": "2026-02-13", "text": "Sample text for schema testing.", "tags": ["lab2", "schema-change"]}
```

Save the file.

---

# Step 4 — Rebuild the API

Since you modified Python code, you must rebuild the container.

```bash
docker compose up -d --build ingestion-api
```

Wait for:

```text
Application startup complete.
```

---

# Step 5 — Re-Run Ingestion

Load your API key:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

Ingest a document containing tags:

```bash
curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Tagged Doc",
    "url": "https://example.com/tagged",
    "source": "Manual",
    "published_date": "2026-02-13",
    "tags": ["lab2", "schema-change"],
    "text": "This document proves schema changes can be applied safely and ingestion still works."
  }'
```

### Expected Output

```json
{
  "status": "ok",
  "weaviate": {
    "id": "...",
    "class": "LabDoc"
  }
}
```

---

# Step 6 — Verify Retrieval Still Works

```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=schema changes applied safely" | python -m json.tool
```

### Expected Output (truncated)

```json
{
  "query": "schema changes applied safely",
  "sources": [
    {
      "title": "Tagged Doc",
      "distance": 0.3,
      "snippet": "This document proves schema changes can be applied safely..."
    }
  ]
}
```

---

# Checkpoints

You have:

- Verified Weaviate readiness
- Verified vectorizer readiness
- Extended API schema safely
- Extended Weaviate schema safely
- Rebuilt containers correctly
- Re-ingested updated documents
- Confirmed semantic retrieval still works

---

# Why This Matters

In real systems:

- Schema changes must be versioned
- API contracts must stay aligned with DB schema
- Rebuilds must be controlled
- Retrieval must be revalidated after changes

---
[Lesson 6](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/1e97e360c828355e4f601fea5a9d57e485a162a5/lessons/06-ingestion-api-validation-and-ingest.md)
