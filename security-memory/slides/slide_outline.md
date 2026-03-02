# Slide Outline — Expanded VSCode Implementation with Weaviate (for Lab 2)

Use this outline to generate a PowerPoint deck.

---

**Slide 1 — Title**
- "Security AI Memory with Weaviate"
- What problem it solves (grounded security guidance)

**Slide 2 — Why we need Expanded VSCode Implementation**
- LLMs hallucinate
- Security requires citations + controls
- Retrieval memory keeps answers grounded

**Slide 3 — Architecture (diagram)**
- NGINX → FastAPI → Weaviate → Ollama embeddings → Ollama LLM
- New: `ExpandedVSCodeMemory` class
- Weaviate uses **classes** (equivalent to Qdrant collections)

**Slide 4 — What Weaviate stores**
- vectors + properties
- Property fields: title / source / tags / text / doc_path / chunk_index
- Schema defined once; vectorizer set to `none` (we supply vectors manually)

**Slide 5 — Ingestion pipeline**
- docs → chunk → embed (Ollama `nomic-embed-text`) → batch upsert (Weaviate `/v1/batch/objects`)
- chunk size & overlap knobs (`SECURITY_CHUNK_CHARS`, `SECURITY_CHUNK_OVERLAP`)
- Deterministic UUIDs → safe to re-run

**Slide 6 — Tool endpoints**
- `GET  /memory/health`
- `POST /memory/query`
- Show example request / response
- Under the hood: Weaviate GraphQL `nearVector` query

**Slide 7 — Student workflow**
- retrieve context → IDE review prompt → minimal diffs → validate lab

**Slide 8 — Prompt library examples**
- Dockerfile review
- docker-compose review
- NGINX review

**Slide 9 — Maintenance + versioning**
- re-ingest loop (idempotent via deterministic UUIDs)
- Delete class + re-ingest when embedding model changes:
  `curl -X DELETE http://localhost:8080/v1/schema/ExpandedVSCodeMemory`

**Slide 10 — Wrap-up**
- What students learned
- Next steps (optional MCP)
