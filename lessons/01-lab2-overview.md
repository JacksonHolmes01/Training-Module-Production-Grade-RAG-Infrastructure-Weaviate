# Lesson 1 — Lab 2 Overview: From Secure DB to a Real RAG App

## Learning objectives

By the end of this lesson, you will be able to:

- Explain what changes from **Lab 1** (secure single-node Weaviate) to **Lab 2** (multi-service RAG system).
- Name each service in the Lab 2 architecture and describe its job in **one sentence**.
- Describe the end-to-end **RAG flow**: *ingest → embed → store → retrieve → generate → show citations*.
- Identify what is **exposed to your laptop** vs what is **internal-only** (and why that matters for security).

---

## Why Lab 2 exists (in plain language)

In **Lab 1**, you deployed Weaviate securely and validated the basics: authentication, RBAC, lifecycle operations, backups, start/stop commands, etc.

That’s the foundation, but in the real world, Weaviate is usually not “the product.” It is an internal part of a bigger application.

In **Lab 2**, we build something that feels like a real application:

- You can open a UI in your browser.
- You can ingest a small dataset.
- You can **chat with your dataset**.
- You can see **which documents were used** (sources) so the answer is verifiable.

This is the “production-grade” mindset:

> Databases are internal. Apps and APIs are what people interact with.

---

## The architecture you will run

This lab uses **Docker Compose** to run multiple containers.

### Services (what each container does)

- **Weaviate**  
  Stores documents and their vector embeddings so we can do semantic retrieval (“find similar meaning”).
- **text2vec-transformers**  
  Generates embeddings (vectors) so Weaviate can do semantic search.
- **Ollama**  
  Runs a local LLM (language model) to generate answers. No OpenAI key needed.
- **Ingestion API (FastAPI)**  
  A backend service that:
  - validates data before it’s stored
  - ingests documents into Weaviate
  - retrieves top relevant docs from Weaviate during chat
  - calls Ollama to generate a grounded answer
- **NGINX (Edge proxy)**  
  The “front door” for API requests. Enforces an API key before traffic can hit the API.
- **Gradio UI**  
  A simple web UI that lets you chat with the system and view status.

---

## What is exposed vs internal-only (important for security)

Only **two** ports are exposed to your laptop:

- `http://localhost:7860` → Gradio UI (chat app)
- `http://localhost:8088` → NGINX proxy (API entrypoint)

Everything else is **internal-only** on the Docker network:

- Weaviate is internal-only (`weaviate:8080`)
- Embedding service is internal-only (`text2vec-transformers:8080`)
- Ollama is internal-only (`ollama:11434`)
- The FastAPI service is internal-only (`ingestion-api:8000`)

### Why we do this

Because exposing a database directly to the internet is risky:

- it increases attack surface
- it bypasses application-level validation
- it makes it harder to apply consistent auth + audit rules

Instead, we expose a **proxy + API** and keep internal systems private.

This is a standard production pattern.

---

## RAG: what it means here

RAG stands for **Retrieval-Augmented Generation**.

In this lab, RAG means:

1. You ask a question in the UI.
2. The API retrieves relevant documents from Weaviate.
3. The API builds a prompt that includes those documents.
4. The API calls Ollama to generate an answer.
5. The API returns:
   - the answer
   - a list of sources (documents used)

### Why the “sources” matter

If you can’t tell where an answer came from, you can’t trust it.

RAG tries to make answers **verifiable** by attaching sources.

---

## How you will know you succeeded (end-of-lab success criteria)

At the end of Lab 2, you should be able to:

- Start the stack with `docker compose up -d --build`
- Load the UI at `http://localhost:7860`
- Ingest sample documents successfully
- Ask questions and receive answers **with sources**
- Run a failure drill (stop a container, see what breaks, recover)

---

## Vocabulary (quick glossary)

- **Container**: a packaged runtime for software (like a lightweight VM).
- **Service**: a container in docker-compose.yml (e.g., `weaviate`, `nginx`).
- **Vector / embedding**: numbers representing meaning of text; used for semantic similarity.
- **Retrieval**: searching the vector DB to find relevant documents.
- **Generation**: producing a text answer from an LLM.
- **Edge proxy**: a gateway service that enforces authentication before traffic reaches internal services.
- **Internal network**: Docker network where containers can talk to each other without being exposed to your laptop.

---

## Checkpoints 

- You can explain what each container does in one sentence.
- You can explain why Weaviate is not exposed to the host.
- You can draw the RAG flow: UI → NGINX → API → (Weaviate retrieval) → (Ollama generation) → UI.

[Lesson 2](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/02-prereqs-and-setup.md)
