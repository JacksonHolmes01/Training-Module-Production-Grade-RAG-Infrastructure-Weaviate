# Lab 2 — Production-Grade RAG Infrastructure (Weaviate + Ollama + API + NGINX + Gradio)

This repository is **Lab 2** in a two-part sequence:

- **Lab 1:** Secure single-node Weaviate fundamentals (auth, RBAC, lifecycle)
- **Lab 2 (this repo):** A **production-style multi-service architecture** where students can **chat with their dataset** using a Retrieval-Augmented Generation (RAG) pipeline.

If you have not completed Lab 1 yet, start there first:
- Lab 1 repo: https://github.com/JacksonHolmes01/Training-Module-Securely-Install-Configure-And-Test-Weviate/tree/main

---

## What students will build

A multi-container deployment using **Docker Compose**:

- **Weaviate** (vector database) — internal-only
- **text2vec-transformers** (embedding generation) — internal-only
- **Ingestion API (FastAPI)** — internal-only; validates input, writes to Weaviate, runs retrieval + LLM calls
- **Ollama** (local LLM runtime) — internal-only; generates grounded answers
- **NGINX** (authentication proxy) — the only public API entrypoint
- **Gradio UI** — browser-based chat app for students

### What makes this “production-grade” (in a lab-friendly way)

- Students do **not** talk to Weaviate directly from the host.
- The **edge proxy** (NGINX) enforces an API key.
- The **API layer** enforces validation and provides a stable interface.
- We add **health checks, logs, and failure drills** so students learn operations.
- We set **memory limits** for major services to force realistic resource thinking.

---

## Quick start

### 0) Clone the repo
```bash
git clone <YOUR-LAB-2-REPO-URL>
cd Training-Module-Production-Grade-RAG-Infrastructure-Weviate
```

### 1) Create your `.env`
```bash
cp .env.example .env
```

Edit `.env` and set:
- `EDGE_API_KEY` (long random string)
- Optional: `OLLAMA_MODEL` (start small if needed)

### 2) Start the stack
```bash
docker compose up -d --build
```

### 3) Pull an Ollama model (one-time)
```bash
./bin/pull_model.sh
```

### 4) Open the UI
- Gradio UI: http://localhost:7860

### 5) Ingest sample data (optional)
```bash
./bin/ingest_sample.sh
```

---

## Lessons

Start here: `lessons/00-lesson-index.md`

---

## Ports (host machine)

- `7860` — Gradio chat UI
- `8088` — NGINX edge proxy (API entrypoint)

> Weaviate is **not** exposed to the host. That is intentional.

---

## Stop / reset

Stop containers (data remains):
```bash
docker compose down
```

Full reset (deletes Weaviate data + Ollama models):
```bash
./bin/reset_all.sh
```


## Quick verification (smoke test)

Run:
```bash
./bin/smoke_test.sh
```

This checks proxy, auth, ingest, retrieval, prompt build, and chat end-to-end.

## Starter dataset (cybersecurity)

The included dataset lives in `data/sample_articles.jsonl` (JSON Lines). It contains short cybersecurity-focused notes (CIA triad, defense in depth, authn/authz, validation, supply chain risk, secrets handling, logging/monitoring, threat modeling, and RAG grounding) designed to produce predictable retrieval results for beginners.

To ingest it:
```bash
./bin/ingest_sample.sh
```
