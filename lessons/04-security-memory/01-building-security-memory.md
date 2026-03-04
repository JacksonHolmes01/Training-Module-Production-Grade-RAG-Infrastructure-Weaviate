# Lesson 4.1 — Building a "Security AI Memory" with Weaviate (Local Vector Database)

**Objective:** Build a local, self-hosted retrieval memory system that stores cybersecurity standards and best practices (NIST, CIS, MITRE, OWASP, Docker hardening, etc.) in Weaviate as searchable embeddings.

**Why this matters:** The RAG assistant (and IDE integrations) should answer security questions using grounded frameworks and controls rather than generating unsupported responses.

## Learning Outcomes

By the end of this lesson, students should be able to:

- Explain what "AI memory" means in the context of this project (and what it does not mean)
- Organize a security corpus inside `security-memory/data/`
- Ingest that corpus into a dedicated Weaviate class (`ExpandedVSCodeMemory`)
- Verify ingestion worked successfully
- Understand how chunking, overlap, tags, and top-k influence retrieval quality

---

## 1) Mental Model (Project Context)

### What "AI memory" means here

In this lab, AI memory = **retrieval memory**. It is not:
- A fine-tuned model
- A system where the model "remembers everything forever"
- A database of model-generated thoughts

It is:
- A curated reference corpus
- Vector embeddings of that corpus
- A searchable Weaviate class
- A retrieval pipeline that feeds relevant chunks into an LLM

The model itself is unchanged. The improvement comes from providing higher-quality context.

---

## 2) What Weaviate Stores

Weaviate uses **classes** (equivalent to Qdrant collections or SQL tables) to organize data. Each object stored in a class contains:

- **Vector** — an embedding (list of floats representing semantic meaning)
- **Properties** — metadata such as:
  - `title`
  - `source`
  - `tags`
  - `chunk_index`
  - `text` (the original chunk)

The vector enables similarity search. The properties provide context to return to the LLM and user.

> **Key difference from Qdrant:** Weaviate calls these "classes" and "objects" rather than "collections" and "points." The concept is identical.

---

## 3) End-to-End Flow

```
Security documents (.md / .txt)
  → chunking (split into smaller pieces)
  → embeddings via Ollama (convert chunks into vectors)
  → Weaviate batch upsert (store vectors + properties)

User question
  → embed the question via Ollama
  → Weaviate nearVector search (top-k chunks)
  → retrieved chunks passed into LLM
  → grounded answer
```

This architecture mirrors production-grade RAG systems.

---

## 4) Folder Structure

```
security-memory/
  data/
    nist/
    cis/
    mitre/
    owasp/
    docker-security/
  scripts/
  prompts/
  docs/
  mcp/
  slides/
```

This folder is intentionally separated from the main lab data. The original lab validates that the RAG pipeline functions correctly. This expanded memory system provides structured reference knowledge.

---

## 5) Adding Datasets

The `security-memory/data/` directory contains the security corpus.

**Recommended file types:**
- `.md` (preferred — preserves structure)
- `.txt`

**Avoid:**
- Raw PDFs (convert to text first)
- Large unstructured file dumps

**Suggested organization:**
```
security-memory/data/
  nist/nist-csf.md
  cis/cis-controls-v8.md
  mitre/attack-enterprise.md
  owasp/owasp-top10.md
  docker-security/cis-docker-benchmark.md
```

This organization improves clarity and tag-based filtering. Files already exist in this folder but feel free to add your own to increase the RAG system's cybersecurity capability.

---

## 6) Separate Weaviate Class

Instead of mixing content into the main `LabDoc` class, this implementation uses:

```
SECURITY_CLASS=ExpandedVSCodeMemory
```

This separation prevents retrieval noise and keeps the security corpus isolated.

> **Weaviate note:** The class schema is automatically created during ingestion if it does not already exist. You do not need to create it manually.

---

## 7) Environment Variables for Retrieval Control

Add to `.env` (already present in `.env.example`):

```env
SECURITY_CLASS=ExpandedVSCodeMemory
SECURITY_TOP_K=6
SECURITY_CHUNK_CHARS=1200
SECURITY_CHUNK_OVERLAP=200
SECURITY_EMBED_MODEL=nomic-embed-text
SECURITY_EMBED_DIM=768
```

**Parameter meanings:**

| Variable | Purpose |
|---|---|
| `SECURITY_TOP_K` | Number of chunks retrieved per query |
| `SECURITY_CHUNK_CHARS` | Size of each chunk in characters |
| `SECURITY_CHUNK_OVERLAP` | Overlap between adjacent chunks |
| `SECURITY_EMBED_MODEL` | Ollama model used for embeddings |
| `SECURITY_EMBED_DIM` | Vector dimension (must match the model) |

Larger chunks provide more context. Smaller chunks improve precision. Overlap prevents boundary context loss.

---

## 8) Running Ingestion

At this stage, the security corpus exists on disk inside `security-memory/data/`. However, Weaviate does not automatically index these files. The documents must be:

1. Read from disk
2. Split into chunks
3. Converted into embeddings via Ollama
4. Inserted into the `ExpandedVSCodeMemory` Weaviate class

This entire pipeline is handled by the ingestion module.

Run thisto apply the additional content to the api:
```bash
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
```

### Why Container Mode Is Recommended

Run ingestion inside the running `ingestion-api` container:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

Based on the number of files being ingested, this could take anywhere from a few minutes to 1–2 hours.

**To monitor progress:**

Open a new terminal tab (`Cmd+T`) and run:
```bash
docker stats
```
If ingestion is active, Ollama CPU usage should be high.

You can also stream the logs:
```bash
docker logs -f ingestion-api
```
This shows chunking progress, embedding calls, and Weaviate batch upload activity.

If these are active and Ollama CPU usage is high — don't cancel. It's just taking time.

### Why container mode works well here

The container already has access to:
- Weaviate (`http://weaviate:8080`) via the internal Docker network
- Ollama (`http://ollama:11434`) for embeddings
- No additional ports need to be exposed to the host

This avoids platform and DNS inconsistencies and guarantees alignment with how the API connects to Weaviate.

### What happens during ingestion

When this command runs:

1. The script scans `security-memory/data/`
2. Each file is read and normalized
3. Content is split into overlapping chunks
4. Each chunk is embedded via Ollama
5. The `ExpandedVSCodeMemory` class is created in Weaviate (if it does not already exist)
6. Chunks are batch-upserted with deterministic UUIDs (safe to re-run)
7. Each stored object contains: the embedding vector, the original text chunk, and metadata (title, source, tags)

If errors occur:
- Check `docker logs ingestion-api`
- Confirm Weaviate is running: `curl http://localhost:8080/v1/meta`
- Confirm Ollama is running: `curl http://localhost:11434/api/tags`
- Verify the class name matches your environment variables

---

## 9) Verifying Ingestion

Ingestion completing without error does not guarantee data was stored correctly. Verification is required.

### Option 1: Weaviate REST API

```bash
curl -sS http://localhost:8080/v1/objects?class=ExpandedVSCodeMemory&limit=1 | python -m json.tool
```

Or check the class schema exists:
```bash
curl -sS http://localhost:8080/v1/schema/ExpandedVSCodeMemory | python -m json.tool
```

Look for `"class": "ExpandedVSCodeMemory"` in the response. This confirms the class was created.

To get an approximate object count:
```bash
curl -sS -X POST http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ Aggregate { ExpandedVSCodeMemory { meta { count } } } }"}' \
  | python -m json.tool
```

**Interpretation:**
- `count > 0` → ingestion succeeded
- `count = 0` → class exists but no objects were inserted
- `404 error` → class does not exist (ingestion did not run)

### Option 2: GraphQL Explorer (Visual)

Weaviate ships with a built-in GraphQL explorer at:

```
http://localhost:8080/v1/explorer
```

Use this query to inspect a few objects:

```graphql
{
  Get {
    ExpandedVSCodeMemory(limit: 3) {
      title
      source
      tags
      text
    }
  }
}
```

This confirms objects were stored with correct properties.

---

## 10) Smoke Test Retrieval

Ingestion verifies storage. Retrieval testing verifies usability.

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"what is OWASP A01", "tags":["owasp"], "top_k":5}'
```

**Expected behavior:** The API should return at least one OWASP-related chunk with a similarity score.

**What this test confirms:**
- Ollama embeddings are working
- Vectors were stored correctly in Weaviate
- Weaviate `nearVector` search is functional
- Property retrieval works
- The retrieval layer is production-ready

**If zero results appear:**
- Ingestion may not have run
- The class name may not match (`SECURITY_CLASS` in `.env`)
- Ollama may not have the embed model pulled — run: `docker exec -it ollama ollama pull nomic-embed-text`
- Files may be improperly formatted
- The query may not match corpus content

---

## Completion Checklist

The lesson is complete when all of the following are true:

- [ ] `security-memory/data/` contains structured reference documents
- [ ] Ingestion runs successfully without errors
- [ ] `ExpandedVSCodeMemory` class exists in Weaviate
- [ ] Object count is greater than zero
- [ ] Retrieval smoke test returns relevant chunks
- [ ] Retrieved chunks contain meaningful properties (title, tags, text)

At this point:
- The security corpus is indexed
- Weaviate is populated
- The retrieval system is validated
- The memory layer is ready for API exposure

---

[Lesson 2 →](02-security-tool-api.md)
