# Lab 2 Lessons Index — Build a Weaviate RAG Chatbot (Step-by-Step)

Follow lessons in order. Each lesson explains **what you are building**, **why it is designed that way**, and **exactly what to configure and run**.

1. [Lesson 1 — Lab 2 Overview (what you’re building)](01-lab2-overview.md)
2. [Lesson 2 — Setup & First Boot (Docker + .env)](02-prereqs-and-setup.md)
3. [Lesson 3 — Compose Architecture (networks, volumes, limits)](03-compose-architecture-and-resource-limits.md)
4. [Lesson 4 — Edge Authentication (NGINX API key)](04-edge-auth-with-nginx.md)
5. [Lesson 5 — Weaviate + Vectorization (schema + embeddings)](05-weaviate-schema-and-vectorization.md)
6. [Lesson 6 — Ingestion API (validate + ingest dataset)](06-ingestion-api-validation-and-ingest.md)
7. [Lesson 7 — RAG Chat (retrieve → generate with Ollama)](07-rag-retrieval-and-ollama.md)
8. [Lesson 8 — Use the Chat UI (Gradio)](08-gradio-chat-ui.md)
9. [Lesson 9 — Operations & Troubleshooting (health, logs, reset)](09-operations-testing-and-troubleshooting.md)

**Dataset:** `data/sample_articles.jsonl` (cybersecurity-focused) ingested via `./bin/ingest_sample.sh`.
