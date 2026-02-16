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

## Step 3 — Guided Build: Add a New Schema Field (tags)

Real-world datasets often include metadata for filtering and organization. In this step, you will expand your system to support a tags field. This allows us to categorize articles (e.g., "security," "tutorial," "production").

---

### 3.1 Update the Request Schema (Data Validation)

First, we must tell our FastAPI application to expect a tags field in incoming JSON requests. If we don't do this, the API will ignore the new data.

1. Open the file: ingestion-api/app/schemas.py
2. Locate the class: Find the class ArticleIn(BaseModel): block.
3. Add the field: Inside the class, add the tags variable. 

Note: Ensure you have List imported from the typing module at the top of the file so Python understands the data type.

--- Python Code ---
from typing import List, Optional

class ArticleIn(BaseModel):
    title: str
    content: str
    # Add the line below:
    tags: List[str] = [] 
---

---

### 3.2 Update Weaviate Collection Definition (Database Schema)

Now that the API accepts the data, Weaviate needs to know how to store it. We specify the dataType as text[] to tell Weaviate this is an array of strings.

1. Open the file: ingestion-api/app/weaviate_client.py
2. Locate the Properties: Find the list of properties for the LabDoc class.
3. Add the Property: Add the following dictionary entry to the existing properties list:

--- JSON Schema ---
{
    "name": "tags",
    "dataType": ["text[]"],
    "description": "Metadata tags for the article"
}
---

---

### 3.3 Update Sample Data

To verify the change, you need data that actually includes these tags.

1. Open the file: data/sample_articles.jsonl
2. Modify a Record: Add the "tags": [...] key to one or more lines. 

Example of a valid line:
{"title": "Secure Deploy", "content": "Keep your keys safe.", "tags": ["security", "lab2"]}

---

### 3.4 Apply and Verify Changes

Because you have modified the application logic and the database structure, you must restart your containers for the changes to take effect.

1. Open a new terminal tab:
   - Windows/Linux: Ctrl + Shift + T
   - macOS: Cmd + T
2. Restart the Ingestion API:
   docker compose restart ingestion-api
3. Check for Errors:
   docker compose logs -f ingestion-api

If you see "Application startup complete," your schema changes were successful!

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

## Checkpoints

- You verified Weaviate and vectorizer readiness.
- You added the `tags` field (schema + request model).
- You ingested a document containing tags successfully.
- Retrieval still returns sources.

[Lesson 6](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/7987f807c10ddbdde34fc021dc3b55fc849e4c9b/lessons/06-ingestion-api-validation-and-ingest.md)
