# Lab 2 — Production-Grade RAG Infrastructure

This repository is **Lab 2** in a two-part sequence.

- **Lab 1:** Secure single-node Weaviate fundamentals  
- **Lab 2 (this repository):** Build a multi-service Retrieval-Augmented Generation (RAG) chatbot using Weaviate, Ollama, FastAPI, NGINX, and Gradio.

You will not just run a chatbot, you will understand how it is built, secured, and operated.

---

# What You Will Build

By the end of this lab, you will have:

- A private vector database (Weaviate)
- A validated ingestion API (FastAPI)
- A local LLM (Ollama) generating grounded answers
- An authentication gateway (NGINX)
- A browser-based chat UI (Gradio)
- A cybersecurity-focused dataset powering retrieval

The system is intentionally layered and secured to resemble real-world deployments.

---

# What Is a RAG System?

**Retrieval-Augmented Generation (RAG)** is a system design pattern that combines:

1. A **retriever** (search system)
2. A **knowledge store** (database of documents)
3. A **language model** (LLM)

Instead of letting the LLM answer from memory alone, RAG works as follows:

1. A user submits a question.
2. The system retrieves relevant documents from a database.
3. The retrieved content is inserted into a structured prompt.
4. The LLM generates an answer grounded in those documents.

This reduces errors and allows the system to answer questions using your own dataset instead of relying purely on pretraining.

---

# How This Architecture Works

This lab implements RAG as a **multi-service system** using Docker.

## High-Level Flow

User → NGINX → FastAPI → Weaviate → Ollama → Response

Each component has a specific responsibility. The services communicate over an internal Docker network so that sensitive components are not exposed to the host machine or the public internet.

---

# System Components Explained

## Weaviate — Vector Database

Weaviate stores:

- Documents (objects)
- Their embeddings (vectors)
- Metadata fields (title, source, tags, etc.)

When you ingest a document:

1. The text is converted into a numeric embedding.
2. The embedding is stored alongside the original document.
3. Future queries are embedded and compared using vector similarity.

This allows **semantic search**, meaning the system retrieves documents based on meaning rather than exact keyword matches.

In this lab, Weaviate is internal-only. It is never exposed directly to the host machine.

---

## text2vec-transformers — Embedding Service

Weaviate does not generate embeddings by itself in this lab.

Instead, it calls a separate service:

- `text2vec-transformers`

This service converts text into vector embeddings using a sentence-transformer model.

This separation teaches an important production concept:

- The database stores vectors.
- A model service generates vectors.
- The two communicate over a defined API boundary.

---

## FastAPI — Application Layer

FastAPI is the core logic layer of the system.

It is responsible for:

- Validating incoming requests
- Enforcing API key authentication (defense in depth)
- Calling Weaviate for retrieval
- Building the LLM prompt
- Calling Ollama for generation
- Returning structured JSON responses

This is where RAG logic lives.

The key operations are:

- `retrieve_sources()`
- `build_prompt()`
- `ollama_generate()`

FastAPI acts as the orchestrator between retrieval and generation.

---

## Ollama — Local Language Model

Ollama runs a local LLM inside Docker.

Its role is generation only.

It does not search.
It does not retrieve documents.
It only generates text from the prompt it is given.

In this lab:

- The prompt already contains retrieved documents.
- The LLM is instructed to use only those sources.
- The model is capped with token limits to prevent runaway responses.

This separation reinforces a core idea:

Retrieval and generation are distinct responsibilities.

---

## NGINX — Edge Gateway

NGINX acts as a boundary between:

- The host machine (external)
- The internal Docker network (protected)

Its responsibilities:

- Enforce an API key before requests reach FastAPI
- Prevent direct exposure of internal services
- Forward validated requests to the ingestion API

Even though FastAPI also checks the API key, this layered enforcement demonstrates **defense in depth**.

In a real production deployment, this role might be handled by:

- An API gateway
- A load balancer
- A cloud edge service

---

## Gradio — Browser UI

Gradio provides a simple browser interface.

It does not contain business logic.
It does not talk to Weaviate directly.

It calls:

NGINX → FastAPI → RAG pipeline

This separation ensures the UI cannot bypass authentication or access internal services directly.

---

# Security Model of This Lab

This lab intentionally demonstrates several security concepts:

- Internal-only database networking
- API key enforcement at the edge
- Validation at the application layer
- Separation of concerns between services
- Controlled LLM prompting to reduce hallucinations
- Docker network segmentation

You are not just building a chatbot.
You are building a layered system with clear boundaries.

---

# Important

The README helps you start the system.

To fully understand:

- Why Weaviate is internal-only  
- Why NGINX enforces an API key  
- How retrieval works  
- How the prompt is constructed  
- How Ollama is called  
- How the services communicate  

Go to:

[Lesson Overview](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/00-lesson-index.md)

Work through the lessons in order.

---

# If You Are Advanced

If you already understand Weaviate, RAG architecture, and containerized systems, go directly to:

[Advanced README](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/Advanced-ReadME.md)

---

This lab is designed not just to teach how to run a RAG system, but how to reason about:

- Architecture
- Boundaries
- Security
- Operational behavior
- Production tradeoffs
