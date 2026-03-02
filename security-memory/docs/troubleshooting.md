# Troubleshooting (Expanded VSCode Implementation + Weaviate Lab)

## 1) `/memory/query` returns 404 or "class not found"

**Meaning:** The `ExpandedVSCodeMemory` class does not exist in Weaviate yet.

**Fix:** Run ingestion — it will auto-create the class schema before inserting objects.

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

## 2) `/memory/health` says `object_count` is 0

**Meaning:** The class exists but is empty — schema was created but no documents were ingested.

**Fix:**
- Add `.md` or `.txt` files under `security-memory/data/`
- Re-run ingestion:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

## 3) Weaviate returns empty nearVector results

**Meaning:** Query vector doesn't match the stored vectors — likely a model mismatch.

**Fix:**
- Confirm `SECURITY_EMBED_MODEL` and `SECURITY_EMBED_DIM` in `.env` match what was used at ingest time
- If you changed models, delete the class and re-ingest:

```bash
curl -X DELETE http://localhost:8080/v1/schema/ExpandedVSCodeMemory
docker exec -i ingestion-api python -m app.security_memory.ingest
```

## 4) Embeddings service timeouts

**Meaning:** Ollama model load or CPU-constrained environment.

**Fix:**
- Retry after a few minutes
- Use a smaller embedding model
- Ensure container image supports your architecture (ARM vs x86)
- Increase timeouts if necessary

## 5) Gradio UI times out but curl works

**Meaning:** UI HTTP client timeout is too small.

**Fix:** Set the UI timeout higher and ensure env parsing is robust.
This pack includes a fixed `gradio-ui/app.py` patch that:
- Reads `GRADIO_HTTP_TIMEOUT_S` safely
- Defaults to 300s when the variable is missing or blank
- Avoids crashing when the env var is empty
