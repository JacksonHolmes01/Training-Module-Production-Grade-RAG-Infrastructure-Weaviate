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
docker exec -i ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://weaviate:8080/v1/.well-known/ready").read().decode())
PY
```

### 2.2 Vectorizer ready?

```bash
docker exec -i ingestion-api python - <<'PY'
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

## Step 3 — Guided Build: Add a New Schema Field (`tags`)

Real-world datasets often include metadata for filtering and organization. In this step, you will expand your system to support a `tags` field.

---

### 3.1 Update the Request Schema (`schemas.py`)

This file defines what data your API is allowed to accept.

**Option A: Using a Code Editor (VS Code, etc.)**
1.  **Open the Sidebar:** On the left side of your editor, expand the `ingestion-api` folder, then the `app` folder.
2.  **Open the File:** Click `schemas.py`.
3.  **Edit:** Find `class ArticleIn(BaseModel):` and add the `tags` line.

**Option B: Using the Terminal (Nano)**
1.  **Run this command:** `nano ingestion-api/app/schemas.py`
2.  **Edit:** Use your arrow keys to move the cursor. Type in the change.
3.  **Save:** Press `Ctrl + O`, then `Enter`. Press `Ctrl + X` to exit.

--- CODE TO ADD ---
class ArticleIn(BaseModel):
    title: str
    content: str
    tags: List[str] = [] 
-------------------

---

### 3.2 Update the Database Schema (`weaviate_client.py`)

Now we must tell the Weaviate database to create a storage space for these tags.

**Option A: Using a Code Editor**
1.  In the sidebar, inside `ingestion-api/app/`, open `weaviate_client.py`.
2.  Find the `properties` list (it currently has "title" and "content").

**Option B: Using the Terminal (Nano)**
1.  **Run this command:** `nano ingestion-api/app/weaviate_client.py`



--- PROPERTY TO ADD ---
{
    "name": "tags",
    "dataType": ["text[]"],
    "description": "Metadata tags for the article"
}
-----------------------

---

### 3.3 Update Sample Data (`sample_articles.jsonl`)

Update your test data so it actually includes the new tags.

**Option A: Editor Sidebar**
1.  Navigate to the `data` folder and open `sample_articles.jsonl`.

**Option B: Terminal (Nano)**
1.  **Run this command:** `nano data/sample_articles.jsonl`

--- EXAMPLE LINE ---
{"title": "Example", "content": "Sample text", "tags": ["lab2", "security"]}
--------------------

---

### 3.4 Apply and Verify Changes

Since you modified the code, you must restart the containers.

1.  **Open a New Terminal Tab:**
    * **Windows/Linux:** `Ctrl + Shift + T`
    * **macOS:** `Cmd + T`
2.  **Restart the Service:**
    ```bash
    docker compose restart ingestion-api
    ```
3.  **Check the Logs:**
    ```bash
    docker compose logs -f ingestion-api
    ```
    *If you see "Application startup complete," your changes are live!*

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
