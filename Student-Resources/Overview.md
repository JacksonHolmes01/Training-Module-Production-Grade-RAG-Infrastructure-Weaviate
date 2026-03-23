# Lab 2 — Weaviate RAG Infrastructure: Repo Overview

> **What this is:** A written walkthrough of this repository for students who are about to start the lab. Read this before lesson 1. It will give you the mental model you need to understand what you are building and why each piece exists.

---

## What You Are Looking At

This repository is a production-grade Retrieval-Augmented Generation (RAG) system. That is a technical term for something conceptually simple: instead of asking an AI a question and hoping it answers from memory, you first search a database of documents for relevant information, then hand that information to the AI as context. The AI generates its answer from what you gave it, not from guesswork.

The system you are building here does that end to end, using real infrastructure: a vector database, an embedding service, an API layer, a local language model, an authentication gateway, and a browser interface. All of it runs locally in Docker containers on your machine.

This is Lab 2 in a two-part sequence. Lab 1 covers Weaviate fundamentals on a single node. This lab takes those foundations and builds a full production-grade RAG system on top of them — layered, secured, and observable.

---

## The Folder Structure

When you look at this repo, here is what each folder is for:

**`ingestion-api/`** — This is the brain of the system. It is a FastAPI application that handles everything: validating documents before they go into the database, retrieving relevant chunks when a user asks a question, building the prompt that gets sent to the language model, and returning the answer. All the RAG logic lives here.

**`data/`** — This is where the documents that power the chatbot live. The system is pre-loaded with a cybersecurity-focused dataset. When you ingest these documents, they get converted into vectors and stored in Weaviate so the system can search them semantically.

**`nginx/`** — Configuration for the NGINX gateway. NGINX sits in front of everything and enforces an API key before any request reaches the application. This is defense in depth — even if someone finds the API, they cannot use it without the key.

**`gradio-ui/`** — A simple Python app that renders the browser chat interface at `http://localhost:7860`. It does not contain any business logic — it just sends your messages to the API and displays the response.

**`security-memory/`** — This is the extended capability you build in the later lessons. It is a separate curated corpus of cybersecurity reference documents (NIST, CIS, MITRE, OWASP) stored in its own dedicated Weaviate class called `ExpandedVSCodeMemory`. When a security-related question is asked, the system pulls relevant chunks from this class and injects them into the prompt to produce grounded, citeable answers.

**`patches/`** — This folder contains the security memory module files that get applied to the running container during the security memory lessons. Unlike the Qdrant version of this lab where the module is baked into the image, the Weaviate version uses a patches approach so you can see exactly what code is being added and why.

**`lessons/`** — The step-by-step lesson files that walk you through building the system. Work through these in order.

**`bin/`** — Helper scripts for setup and teardown.

---

## The Five Services

This system runs as five Docker containers that communicate over an internal network. Here is what each one does:

**Weaviate** — The vector database. It stores your documents as objects inside a class called `LabDoc`, alongside their vector embeddings and metadata fields like title, source, and tags. When you search, Weaviate finds the objects whose vectors are closest to your query vector using cosine distance — lower distance means better match. Weaviate runs internally and is never exposed directly to your machine — only the API can talk to it.

**text2vec-transformers** — A separate embedding service that is tightly integrated with Weaviate. Unlike some other vector databases that require you to generate embeddings separately before inserting, Weaviate calls this service automatically whenever you insert or query a document. You do not need to manage embedding calls in your ingestion code — Weaviate handles it. This service uses a sentence-transformer model and runs internally on port 8080.

**ingestion-api** — The FastAPI application described above. It runs internally on port 8000 and is only reachable through NGINX.

**edge-nginx** — The authentication gateway. It runs on port 8088 on your machine. Every request to the API goes through here first. If the `X-API-Key` header is missing or wrong, NGINX rejects the request before it ever reaches FastAPI.

**Gradio** — The browser UI. It runs on port 7860 and is the only service you interact with directly through a browser. It calls the API through NGINX, so authentication is enforced even from the UI.

---

## The High-Level Flow

When you type a question in the chat interface, here is exactly what happens:

```
You → Gradio → NGINX (auth check) → FastAPI → Weaviate (retrieve chunks)
                                             → build prompt with chunks
                                             → Ollama (generate answer)
                                             → return answer to you
```

Every step is explicit and observable. Nothing is hidden in a black box. This is intentional — the lab is designed to teach you how to reason about each layer, not just run it.

---

## How Weaviate Differs From Qdrant

If you completed Lab 1 (Qdrant), a few things will look different here:

**Class-based schema** — Weaviate uses classes to define data structure. The main collection is called `LabDoc` and has defined properties. You cannot add or remove properties after the class is created without recreating it. Qdrant uses collections with flexible payload fields.

**Automatic embeddings** — In the Qdrant lab, Ollama generates embeddings and you insert them manually. In this lab, Weaviate calls `text2vec-transformers` automatically whenever you insert a document. Your ingestion code just sends the text — Weaviate handles the rest.

**Distance scoring** — Weaviate returns distance scores where lower is better (closer to 0 means stronger match). Qdrant returns similarity scores where higher is better. Keep this in mind when interpreting retrieval results.

**GraphQL query interface** — Weaviate uses GraphQL for queries rather than a REST payload structure. You will see this when verifying ingestion and when the store layer queries the collection.

**Patches folder** — The security memory module is applied via `docker cp` rather than being baked into the image. This means you need to reapply it after container rebuilds.

---

## The Security Memory Extension

In lessons 4.1 through 4.3 you extend the base system with a security memory layer. This adds a dedicated Weaviate class called `ExpandedVSCodeMemory` that stores chunked cybersecurity reference documents. When a question is detected as security-related, the system automatically fetches relevant chunks from this class and injects them into the prompt alongside the regular RAG sources.

This means the AI's answer is no longer based just on the dataset documents — it is also grounded in actual security standards like CIS Benchmarks and OWASP controls. The `/memory/query` endpoint exposes this class so you can query it directly from the terminal or your IDE.

---

## What Makes This Different From a Tutorial

Most RAG tutorials give you a script that calls an API and prints an answer. This lab gives you a system:

- Authentication is enforced at two layers (NGINX and FastAPI)
- The database is internal-only and never exposed
- The UI is decoupled from the API
- The embedding service is separate from the storage service
- The security memory is isolated in its own Weaviate class
- Every component has observable logs and health endpoints

These are the patterns used in real production deployments. You are not just learning how RAG works — you are learning how to build and operate a secured, layered AI system.

---

## Before You Start Lesson 1

Make sure you have:
- Docker Desktop installed and running
- At least 16GB of RAM available (Ollama and text2vec-transformers both need memory)
- Your `.env` file configured with a strong `EDGE_API_KEY`

Then start the system:

```bash
docker compose up -d
```

Give it 60–90 seconds for all services to initialize, then open `http://localhost:7860` to confirm the UI is running.

When you are ready, go to `lessons/00-lesson-index.md` and start from lesson 1.
