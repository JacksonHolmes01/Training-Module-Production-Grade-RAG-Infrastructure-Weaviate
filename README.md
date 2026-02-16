# Lab 2 — Production-Grade RAG Infrastructure

This repository is **Lab 2** in a two-part sequence.

- Lab 1: Secure single-node Weaviate fundamentals  
- Lab 2 (this repository): Build a multi-service Retrieval-Augmented Generation (RAG) chatbot using Weaviate, Ollama, FastAPI, NGINX, and Gradio.

You will not just run a chatbot — you will understand how it is architected, secured, and operated.

---

# What You Will Build

By the end of this lab, you will have:

- A private vector database (Weaviate)
- A validated ingestion API
- A local LLM (Ollama) generating grounded answers
- An authentication gateway (NGINX)
- A browser-based chat UI
- A cybersecurity-focused dataset powering retrieval

The system is intentionally layered and secured to resemble real-world deployments.

---

# Getting Started

## 1. Clone the repository

```bash
git clone <YOUR-REPO-URL>
cd Training-Module-Production-Grade-RAG-Infrastructure-Weaviate
```

## 2. Create your environment file

```bash
cp .env.example .env
```

## 2. Create your environment file

Copy the example environment file:

    cp .env.example .env

Open the newly created `.env` file in a text editor.

Inside that file, you will see a line like:

    EDGE_API_KEY=

You must set this to a long, random string.

### What is `EDGE_API_KEY`?

This is a shared secret (like a password) that protects your API.

In this lab:

- NGINX checks for this key before allowing requests through.
- If the key is missing or incorrect, the request is rejected.
- This models how real production systems protect backend services.

### How to generate a secure key

In your terminal, run:

    openssl rand -hex 32

This will generate a long random string, for example:

    a3f92d1e8b7c6f4d9a2e1c3b5f6a7d8c9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4

Copy that entire string and paste it into your `.env` file like this:

    EDGE_API_KEY=a3f92d1e8b7c6f4d9a2e1c3b5f6a7d8c9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4

Save the file.

Important:
- Do NOT share this key.
- Do NOT commit your `.env` file to GitHub.
- Only the proxy and API need to know this value.

Once this is set, your system will require that key for any API request, which is how we enforce authentication at the edge.


## 3. Start the stack

```bash
docker compose up -d --build
```

## 4. Pull the model (one-time)

```bash
./bin/pull_model.sh
```

## 5. Ingest the dataset

```bash
./bin/ingest_sample.sh
```

## 6. Open the UI

http://localhost:7860

If everything is working, you should be able to ask cybersecurity-related questions and receive answers with sources.

---

# Important

The README only helps you start the system.

To understand:

- Why Weaviate is internal-only  
- Why NGINX enforces an API key  
- How retrieval works  
- How the prompt is constructed  
- How Ollama is called  
- How the services communicate  

Go to:

```
lessons/00-lesson-index.md
```

Work through the lessons in order.


