
# Lab 2 — Building a Production-Style RAG Chatbot  
*(Weaviate + Ollama + FastAPI + NGINX + Gradio)*

This repository is **Lab 2** in a two-part sequence.

- **Lab 1:** Secure single-node Weaviate fundamentals  
- **Lab 2 (this repository):** Build a complete, production-style Retrieval-Augmented Generation (RAG) chatbot using multiple services working together.

If you have not completed Lab 1, start there first:

Lab 1 repository:  
https://github.com/JacksonHolmes01/Training-Module-Securely-Install-Configure-And-Test-Weviate

---

# What You Are Building

By the end of this lab, you will have:

- A working chatbot running in your browser  
- A private vector database (Weaviate)  
- A local LLM (Ollama) generating answers  
- An API layer enforcing validation  
- An authentication proxy protecting your system  
- A cybersecurity-focused dataset you can chat with  

This is not “just a chatbot.”

It is a **secure, multi-service architecture** designed to resemble how real systems are built.

---

# What Makes This “Production-Style”

Even though this is a lab, the design mirrors real-world systems:

- Weaviate is **not exposed to the internet**
- All traffic flows through an **NGINX edge proxy**
- The API enforces validation and controls database access
- Services are isolated using Docker networking
- Memory limits are applied to simulate real infrastructure constraints
- Health checks and logs are used for troubleshooting

You are not just learning how to run a bot —  
you are learning how to **architect and operate** one safely.

---

# Architecture Overview

This lab runs using Docker Compose and includes:

- **Weaviate** — stores documents and embeddings (internal only)  
- **text2vec-transformers** — generates embeddings (internal only)  
- **FastAPI (Ingestion + RAG API)** — validates input, retrieves documents, calls the LLM  
- **Ollama** — local LLM runtime (generates grounded responses)  
- **NGINX** — API gateway enforcing an API key  
- **Gradio UI** — browser-based chat interface  

All services communicate over an internal Docker network.

Only two ports are exposed to your machine:

- `7860` — Chat UI  
- `8088` — API gateway (NGINX)  

Weaviate is intentionally not exposed.

---

# Before You Start

You need:

- Docker Desktop installed and running  
- At least 8–16 GB of RAM available  
- Basic comfort using the terminal  

---

# Step-by-Step Setup (Beginner Friendly)

## Step 1 — Clone the Repository

    git clone <YOUR-LAB-2-REPO-URL>
    cd Training-Module-Production-Grade-RAG-Infrastructure-Weviate

This downloads all configuration files and service code.

---

## Step 2 — Create Your Environment File

Copy the example environment file:

    cp .env.example .env

Why this matters:

The `.env` file stores configuration values like:

- Your API key  
- Which LLM model to use  
- Service settings  

Open `.env` in a text editor and set:

    EDGE_API_KEY=your-long-random-string

You can generate a random key using:

    openssl rand -hex 32

Paste the output into `.env`.

Do **not** commit `.env` to GitHub.

---

## Step 3 — Start the System

Run:

    docker compose up -d --build

What this does:

- Builds container images  
- Starts all services  
- Connects them through Docker networking  

The first run may take several minutes.

Check container status:

    docker compose ps

All services should show as running.

---

## Step 4 — Pull the LLM Model (One Time Only)

Ollama requires a model to generate responses.

Run:

    ./bin/pull_model.sh

This downloads the default model specified in `.env`.

This step only needs to be done once.

---

## Step 5 — Ingest the Cybersecurity Dataset

Before chatting, load documents into Weaviate:

    ./bin/ingest_sample.sh

This ingests:

    data/sample_articles.jsonl

The dataset includes cybersecurity topics such as:

- CIA triad  
- Defense in depth  
- Authentication vs authorization  
- Input validation  
- Supply chain risk  
- Logging and monitoring  
- Threat modeling  
- RAG grounding and citations  

---

## Step 6 — Open the Chatbot

Open your browser:

    http://localhost:7860

Try asking:

- “Explain defense in depth using this lab as an example.”
- “What is the difference between authentication and authorization?”
- “Why is exposing a database directly risky?”
- “What is supply chain risk in AI pipelines?”

Each response should include:

- An answer  
- A **Sources** section listing retrieved documents  

That means your RAG pipeline is working.

---

# How the Chatbot Actually Works

When you send a message:

1. Your browser sends the request to the **Gradio UI**  
2. The UI sends it to **NGINX**  
3. NGINX checks the API key  
4. The request reaches the **FastAPI** service  
5. FastAPI retrieves relevant documents from **Weaviate**  
6. FastAPI sends those documents to **Ollama**  
7. Ollama generates a grounded answer  
8. The answer and sources are returned to the browser  

This is a secure, layered architecture.

---

# If Something Breaks

Check in this order:

### 1. Are containers running?

    docker compose ps

### 2. Is the proxy responding?

    curl -i http://localhost:8088/proxy-health

### 3. Is the API responding?

    curl -i -H "X-API-Key: YOUR_KEY" http://localhost:8088/health

### 4. Check logs

    docker compose logs --tail=200

---

# Stop or Reset

Stop containers (keep data):

    docker compose down

Full reset (delete database + model data):

    ./bin/reset_all.sh

---

# Starter Dataset (Cybersecurity)

The included dataset lives in:

    data/sample_articles.jsonl

It contains short cybersecurity-focused notes designed to produce predictable retrieval results for beginners.

To re-ingest:

    ./bin/ingest_sample.sh

---

# Lessons

Start here:

    lessons/00-lesson-index.md

Each lesson explains:

- What component you are configuring  
- Why it exists  
- How it connects to the system  
- How to verify it works  

By the end, you will not only have a working chatbot —  
you will understand how and why it works.
```
