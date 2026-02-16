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
cd Training-Module-Production-Grade-RAG-Infrastructure-Weviate
```

## 2. Create your environment file

```bash
cp .env.example .env
```

Set a strong value for:

```
EDGE_API_KEY=
```

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


