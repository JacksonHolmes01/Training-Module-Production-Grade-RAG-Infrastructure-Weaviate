# Maintaining Expanded VSCode Implementation (Production-Grade Notes)

## The core rule

Embeddings define the vector space. If you change your embeddings model or dimension,
you are no longer comparable to the existing vectors.

## When you MUST create a new class

- model ID changes (e.g., MiniLM → BGE)
- embedding dimension changes (384 → 768)
- distance metric changes (Cosine → Dot)

> **Weaviate note:** Weaviate uses **classes** instead of Qdrant's collections.
> To "recreate" a class, delete it via the Weaviate REST API and re-ingest.

Recommended practice:

- Keep old class as `ExpandedVSCodeMemory_v1_minilm`
- Create new class as `ExpandedVSCodeMemory_v2_bge`
- Update `.env` → `SECURITY_CLASS` to point to the latest
- Re-ingest

**To delete a class in Weaviate:**
```bash
curl -X DELETE http://localhost:8080/v1/schema/ExpandedVSCodeMemory
```

## Re-ingest (safe, idempotent)

If you only add new docs or edit existing docs:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

This uses upserts (via deterministic UUIDs) and can be run repeatedly without
creating duplicates.

## Chunking policy

Chunk size affects:
- **precision** — smaller chunks retrieve more precisely
- **context** — larger chunks have more meaning but may include noise

Practical defaults for security frameworks:
- 1000–1500 char chunks
- 150–250 char overlap

If students complain results are too vague:
- Reduce chunk size (e.g., 900)
- Increase `top_k` (e.g., 8)

## Governance / licensing note

Many frameworks have usage terms. For an educational repo, you typically:
- Link to official sources
- Include small excerpts
- Avoid redistributing full copyrighted content unless permitted
