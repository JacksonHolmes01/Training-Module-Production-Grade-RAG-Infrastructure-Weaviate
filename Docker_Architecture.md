# Docker in This Repo: A Textbook-Style Deep Dive (Lab 2 RAG System)

This document explains, at a systems level, **how and why Docker is used in this repository**. It is written so you can understand what you built before you change it.

---

## Table of Contents

1. What Docker is (and what it is not)
2. The mental model: images, containers, networks, volumes
3. The Lab 2 architecture: who talks to whom and why
4. `docker-compose.yml` as an orchestration contract
5. Networking in this repo (internal-only design)
6. Data persistence with volumes (why your data survives restarts)
7. Startup sequencing vs readiness (why `depends_on` is not enough)
8. Resource limits (`mem_limit`) and performance troubleshooting
9. Logging, observability, and “where did my request go?”
10. Practical commands: day-to-day operations
11. Failure modes and how to debug them methodically
12. Security rationale: boundaries, secrets, and exposure control
13. Appendix: a guided “trace a request” walkthrough

---

# 1. What Docker Is (and What It Is Not)

## 1.1 The problem Docker solves
When you build a real system, you are rarely running *one* program. You are running:

- a database
- a model server
- an API
- a proxy
- a UI
- plus supporting dependencies

Without Docker, you would need to install and configure all of those on your machine **in the correct versions**, and then keep them compatible. That is hard to teach and hard to replicate.

Docker gives you a way to say:

> “Run this system the same way on every student machine.”

## 1.2 A common misconception
Docker is not a virtual machine. A VM bundles an entire operating system kernel. Docker containers share the host kernel, so they start faster and use less overhead.

What you get is:

- an isolated filesystem for each service
- its own process space
- its own networking identity
- reproducible startup and configuration

---

# 2. The Core Mental Model: Images, Containers, Networks, Volumes

## 2.1 Images
An **image** is the packaged artifact: code + dependencies + runtime environment.

In this repo:
- `nginx:1.27-alpine` is an image pulled from Docker Hub
- `ollama/ollama:latest` is an image pulled from Docker Hub
- `semitechnologies/weaviate:1.25.7` is an image pulled from Docker Hub
- `ingestion-api` is built from your local `./ingestion-api` folder

## 2.2 Containers
A **container** is a running instance of an image.

You can think of it as:
- image = blueprint
- container = house built from the blueprint and currently occupied

A container can be stopped and restarted. Unless you attach a **volume**, its internal filesystem changes are usually ephemeral.

## 2.3 Networks
Docker networks create **private virtual LANs** for containers.

In this repo you use one main network:

- `internal` (bridge network)

Key concept: if a container is not bound to the host with `ports:`, it is not reachable from your laptop browser/terminal, only from other containers.

## 2.4 Volumes
Volumes are Docker-managed persistent storage.

In this repo:
- `weaviate_data` stores the Weaviate database contents
- `ollama_data` stores pulled Ollama models and cache

That is why you can restart containers without losing:
- your ingested documents
- your downloaded models

---

# 3. The Lab 2 Architecture: Who Talks to Whom, and Why

This system is a **layered RAG architecture**. Each service has one job.

## 3.1 Services and responsibilities

### Weaviate (vector database)
- Stores documents and metadata
- Stores vectors (embeddings) used for semantic search
- Answers: “Which documents are most relevant to this query?”

### text2vec-transformers (embedding service)
- Converts text → numeric vector
- Weaviate calls it automatically when you store a document (because you configured it as the vectorizer)

### Ollama (local LLM runtime)
- Runs the language model you pulled (e.g., `llama3.2:1b`)
- Generates an answer given a prompt

### ingestion-api (FastAPI)
- Ingests documents into Weaviate with validation
- Performs retrieval for a question
- Builds a grounded prompt (question + sources)
- Calls Ollama to generate a response

### NGINX (edge gateway)
- Exposes one host port (`8088`)
- Enforces an API key before traffic reaches the API
- Proxies requests to the internal API container

### Gradio UI
- Browser interface for chat
- Talks to NGINX, not directly to the API

## 3.2 Why this is “production-like”
Because it has:
- service boundaries
- a gateway
- authentication
- internal-only databases
- a UI that only sees the gateway, not the database

This is a minimal version of how real RAG systems are deployed.

---

# 4. `docker-compose.yml` as an Orchestration Contract

Compose is a human-readable contract that says:

- which services exist
- which images build/run them
- what environment variables they need
- what they can reach on the network
- what persistent storage they use
- what ports (if any) are exposed to your machine

## 4.1 Build vs pull
- `image:` means pull from a registry (Docker Hub by default)
- `build:` means “use this folder to build a new local image”

You use both:
- Weaviate, Ollama, NGINX pull pinned images
- `ingestion-api` builds from your source

## 4.2 Ports vs networks
- `ports:` exposes container ports to the host
- `networks:` connects containers privately

The design here is intentional:
- only NGINX and Gradio expose ports to the host
- Weaviate, transformers, and Ollama stay internal

---

# 5. Networking in This Repo: Internal-Only Design

## 5.1 Service discovery by name
On a Docker network, services can reach each other by **service name**:

- `http://weaviate:8080`
- `http://text2vec-transformers:8080`
- `http://ollama:11434`

Example internal call from the API container:
```bash
docker exec -i ingestion-api python -c "import urllib.request; print(urllib.request.urlopen('http://ollama:11434/api/tags').read()[:120])"
```

## 5.2 Why the database is not exposed
If Weaviate were exposed to the host (`ports: "8080:8080"`), then:
- anyone on your network could potentially hit it
- students would normalize unsafe design
- you would lose the “defense-in-depth” lesson

This repo is teaching: put sensitive services behind boundaries.

---

# 6. Data Persistence: Why Your Data Survives Restarts

## 6.1 Weaviate data volume
Weaviate writes its index and objects to `/var/lib/weaviate`.

Your compose mounts:
- `weaviate_data:/var/lib/weaviate`

So when the container is recreated:
- the data directory is still there
- Weaviate loads the database from the volume

## 6.2 Ollama models volume
Ollama stores pulled models under:
- `/root/.ollama`

You mount:
- `ollama_data:/root/.ollama`

So “pull once, reuse forever” (unless you delete the volume).

---

# 7. Startup Sequencing vs Readiness

## 7.1 `depends_on` only controls start order
Compose’s `depends_on` guarantees:
- container A starts before container B

It does **not** guarantee:
- A is ready to accept requests

That’s why you also use:
- `/v1/.well-known/ready` checks
- healthchecks on services

## 7.2 The readiness pattern
A production pattern is:
1. start containers
2. poll readiness endpoints
3. only then allow traffic

Your API’s `/health` endpoint checks Weaviate readiness as a teaching example.

---

# 8. Resource Limits (`mem_limit`) and Performance

This lab uses ML services that can eat RAM.

## 8.1 Why limits exist
- to prevent one container from freezing your whole machine
- to teach capacity planning

## 8.2 What happens when RAM is too low
- models load slowly
- generation takes forever
- processes get killed (OOM)

## 8.3 If your machine struggles
You can reduce `mem_limit` values.

Example (not required):
- set Ollama to 4 GB:
  - change `mem_limit: 8g` → `mem_limit: 4g`

Also consider switching to a smaller model in `.env`.

---

# 9. Logging, Observability, and “Where Did My Request Go?”

When you hit `/chat`, the request path is:

1. Host terminal → `localhost:8088`
2. NGINX checks API key
3. NGINX proxies → `ingestion-api:8000`
4. API retrieves from Weaviate (GraphQL)
5. API builds prompt
6. API calls Ollama to generate

If something fails, logs tell you where:

```bash
docker compose logs -f nginx
docker compose logs -f ingestion-api
docker compose logs -f weaviate
docker compose logs -f ollama
```

A debugging best practice is to test each layer independently:

- `GET /proxy-health` (gateway)
- `GET /health` (API + Weaviate ready)
- `GET /debug/retrieve` (retrieval)
- `POST /debug/prompt` (prompt construction)
- `POST /debug/ollama` (generation only)
- `POST /chat` (full pipeline)

---

# 10. Practical Commands: Day-to-Day Operations

## Start everything
```bash
docker compose up -d
```

## Stop everything (containers only)
```bash
docker compose down
```

## Stop everything and delete volumes (danger: deletes Weaviate data + models)
```bash
docker compose down -v
```

## Rebuild a single service you changed
```bash
docker compose up -d --build ingestion-api
```

## Watch live logs
```bash
docker compose logs -f ingestion-api
```

## Exec into a container
```bash
docker exec -it ingestion-api bash
```

---

# 11. Failure Modes and How to Debug Them

## 11.1 You get 401 from NGINX
- Your header is missing `X-API-Key`
- Your key doesn’t match the value NGINX has

Confirm:
```bash
echo "Key length: ${#EDGE_API_KEY}"
curl -sS -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/proxy-health
```

## 11.2 Retrieval returns empty sources
Possible causes:
- you did not ingest documents
- Weaviate schema missing fields
- vectorizer not ready
- you are querying a class that doesn’t exist

Confirm ingestion exists:
```bash
docker exec -i ingestion-api python -c "import urllib.request; print(urllib.request.urlopen('http://weaviate:8080/v1/objects?class=LabDoc&limit=1').read()[:200])"
```

## 11.3 `/chat` hangs but debug endpoints work
That usually means:
- overall orchestration timeout missing
- Ollama generation takes too long
- concurrency issue (async glue)

This is why the lab teaches layer isolation.

---

# 12. Security Rationale: Boundaries, Secrets, Exposure Control

## 12.1 Defense in depth
You are enforcing API key checks:
- at NGINX (gateway boundary)
- inside the app (application boundary)

That redundancy is intentional.

## 12.2 Secret handling in `.env`
`.env` is a local convenience. In real systems you would use:
- a secret manager
- CI/CD injection
- rotation

But the mental model is the same: secrets should not be hardcoded.

---

# 13. Appendix: Trace a Request End-to-End

Run this set in order:

1) Gateway health:
```bash
curl -sS -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/proxy-health
```

2) Retrieval only:
```bash
curl -sS -G "http://localhost:8088/debug/retrieve" -H "X-API-Key: $EDGE_API_KEY" --data-urlencode "q=CIA triad" | python -m json.tool
```

3) Prompt build:
```bash
curl -sS -X POST "http://localhost:8088/debug/prompt" -H "Content-Type: application/json" -H "X-API-Key: $EDGE_API_KEY" -d '{ "message": "What is the CIA triad? Answer in 2 sentences." }' | python -m json.tool
```

4) Generation only:
```bash
curl -sS -X POST "http://localhost:8088/debug/ollama" -H "Content-Type: application/json" -H "X-API-Key: $EDGE_API_KEY" -d '{ "message": "Explain CIA triad in 2 sentences." }' | python -m json.tool
```

5) Full pipeline:
```bash
curl -sS -X POST "http://localhost:8088/chat" -H "Content-Type: application/json" -H "X-API-Key: $EDGE_API_KEY" -d '{ "message": "What is the CIA triad? Answer in 2 sentences." }' | python -m json.tool
```

If 1–4 work but 5 fails, your *glue logic* is the problem (timeouts, async, error handling).

---

## Notes for instructors
Good “safe” exercises include:
- adding a metadata field like `tags`
- adding a new debug endpoint
- changing the prompt template
- pinning images to specific versions
- adding an explicit readiness gate before enabling chat
