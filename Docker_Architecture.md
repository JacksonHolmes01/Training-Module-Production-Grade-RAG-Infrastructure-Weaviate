# Docker in This Repo: A Textbook-Style Deep Dive

This document explains, at a systems level, how and why Docker is used in the Weaviate-based RAG repository. It is written so you can understand what you built before you change it.

Read this before modifying any Docker configuration, adding services, or debugging infrastructure issues. The goal is not to memorize commands — it is to build a mental model accurate enough that when something breaks, you can reason about where and why.

## Table of Contents

1. What Docker is and what problem it solves
2. The core mental model: images, containers, networks, volumes
3. The lab architecture: who talks to whom and why
4. docker-compose.yml as an orchestration contract
5. Networking in this repo: the internal-only design
6. Data persistence with volumes
7. Startup sequencing vs readiness
8. Resource limits and performance
9. Logging and observability
10. Practical commands for day-to-day work
11. Debugging failure modes methodically
12. Security rationale: boundaries, secrets, and exposure control
13. Appendix: tracing a request end-to-end

---

## 1. What Docker Is and What Problem It Solves

When you build a real system, you are rarely running one program. You are running a vector database, an embedding model, an API, a gateway, and sometimes a UI — all at once, all needing to be compatible versions, all needing to find each other on a network.

Without Docker, you would need to install and configure all of those on your own machine in the correct versions and then keep them compatible. On the next student's machine, the same setup might fail because they have a different OS, a different Python version, or a missing system library.

Docker solves this by packaging each service — its code, dependencies, and runtime environment — into a self-contained unit called an image. When you run the lab with `docker compose up -d`, every student gets the exact same services running in the exact same way, regardless of what is installed on their machine.

That is the core educational reason Docker is used here: it makes the lab reproducible.

### What Docker is not

Docker is not a virtual machine. A VM bundles an entire operating system kernel. Docker containers share the host kernel, which means they start faster and use less memory than full VMs. What you get is an isolated filesystem, its own process space, its own network identity, and reproducible startup — without the overhead of a full OS.

---

## 2. The Core Mental Model: Images, Containers, Networks, Volumes

Before reading about the specific services in this repo, it helps to have these four concepts clearly defined.

### Images

An image is a packaged, read-only artifact: code, dependencies, and runtime environment bundled together. In this repo you use a mix of prebuilt images pulled from registries (such as `nginx:1.27-alpine`, `semitechnologies/weaviate:1.24.6`, and `ollama/ollama:latest`) and locally built images (such as `ingestion-api` and `gradio-ui`, which are built from Dockerfiles in the repo).

### Containers

A container is a running instance of an image. A useful way to think about it: an image is a blueprint, and a container is the building constructed from that blueprint and currently in use. You can run multiple containers from the same image, stop and restart them, and unless you have attached persistent storage, any changes written inside the container are lost when it is removed.

### Networks

Docker networks create private virtual LANs for containers. In this repo, all services are connected to a network called `internal`. Containers on the same network can reach each other by service name (for example, `http://weaviate:8080`) using Docker's built-in DNS. Containers not connected to a network, or on different networks, cannot reach each other.

This is important: if a service is not listed under `ports:` in `docker-compose.yml`, it is not reachable from your laptop. It is only reachable from other containers on the same network. This is intentional — databases and model servers should not be publicly accessible.

### Volumes

Volumes are Docker-managed persistent storage that lives outside the container filesystem. In this repo, `weaviate_data` stores the Weaviate database and `ollama_data` stores downloaded models. Because these are volumes, you can stop and recreate containers without losing your ingested documents or downloaded models.

If you run `docker compose down` and then `docker compose up -d`, your data is still there.

---

## 3. The Lab Architecture: Who Talks to Whom and Why

This system is a layered RAG architecture. Each service has exactly one job, and they communicate through well-defined interfaces. Understanding who calls whom is the foundation of being able to debug the system.

### Weaviate (vector database)

Weaviate stores two things for every document you ingest: a **vector** (a list of numbers representing the meaning of the text) and **properties** (the metadata and text you want to get back when the document is retrieved). When you ask a question, Weaviate answers: "given this query vector, which stored vectors are most similar?"

Weaviate organizes data into **classes** — roughly equivalent to database tables. In this lab, the main class is `LabDoc` and the security memory class is `ExpandedVSCodeMemory`. Each class has a schema defining its properties.

One important aspect of this setup: Weaviate is configured with `vectorizer: none`, meaning it does not generate embeddings itself. You must generate embeddings elsewhere and send the vector to Weaviate. That is the job of the embeddings service.

### Embeddings service (model server)

The embeddings service converts text into a numeric vector. In this repo, embeddings are generated using **Ollama** with the `nomic-embed-text` model. The ingestion API calls the Ollama embeddings endpoint to get a vector, then sends that vector to Weaviate.

### Ollama (local LLM runtime)

Ollama runs the local language model you pulled (for example, `llama3.1`). It takes a prompt as input and returns generated text as output. In the RAG flow, it is the final step: it receives a prompt that includes the retrieved sources and the user's question, and generates the answer.

Ollama serves two roles in this lab: **embedding** (via `/api/embeddings`) and **generation** (via `/api/generate` or `/api/chat`). Both go through the same Ollama service.

### ingestion-api (FastAPI)

The ingestion API is the brain of the system. It handles two main workflows.

For **ingestion**: it receives a document, calls Ollama to convert the text to a vector, and upserts the vector plus properties into Weaviate using the batch API.

For **chat**: it receives a question, embeds the question via Ollama, queries Weaviate using a `nearVector` GraphQL query to find the most similar documents, builds a prompt that includes the question and the retrieved sources, calls Ollama to generate an answer, and returns the answer along with the sources it used.

### NGINX (edge gateway)

NGINX is the only service exposed on a host port (8088). It sits in front of the ingestion API and does two things: it checks that every incoming request has a valid API key, and it proxies authenticated requests to the ingestion API. Nothing reaches the API without going through NGINX first.

### Gradio UI

The Gradio UI is the browser-based chat interface. It talks to NGINX, not directly to the ingestion API. This means it goes through the same authentication layer as any other client. It displays the answer and the sources retrieved from Weaviate.

### The production-like design goal

This lab is designed to mirror how real RAG systems are structured. It has service boundaries, a gateway with authentication, internal-only databases and model servers, and a UI that only sees the gateway. Understanding this architecture means you understand the patterns used in production systems, not just a toy demo.

---

## 4. docker-compose.yml as an Orchestration Contract

The `docker-compose.yml` file is more than a startup script. It is a human-readable contract that documents the entire architecture in one place. It specifies which services exist, which images run them, what environment variables they need, what network they are on, what persistent storage they use, which ports (if any) are exposed to your machine, and what healthchecks determine whether a service is ready.

When you read `docker-compose.yml`, you are reading the architecture. When you change it, you are changing the architecture. That is why it is worth understanding every section rather than treating it as a configuration file to ignore.

---

## 5. Networking in This Repo: The Internal-Only Design

All services in this repo are on a single bridge network called `internal`. This means they can reach each other by service name, but they are not reachable from outside Docker unless explicitly published.

The only published ports are NGINX (8088) and Gradio (7860). Weaviate (8080) is also published in this repo for debugging and inspection, but in a production environment it would not be.

The most important networking rule to remember: **inside a container, `localhost` refers to the container itself, not your host machine.** If you try to call `http://localhost:8080` from inside the `ingestion-api` container, it will fail because Weaviate is not running inside that container. The correct address is `http://weaviate:8080`, using the service name as the hostname.

This trips up many students. If you see a connection error inside a container, check whether you are using `localhost` when you should be using a service name.

---

## 6. Data Persistence with Volumes

Without volumes, every time you recreate a container its internal filesystem starts fresh. For Weaviate, that would mean losing all your ingested documents. For Ollama, that would mean re-downloading models every time.

Volumes solve this by storing data outside the container in Docker-managed storage. The mappings in `docker-compose.yml` are:

- `weaviate_data:/var/lib/weaviate` — Weaviate's database files
- `ollama_data:/root/.ollama` — Ollama's downloaded models and cache

These volumes persist across `docker compose down` and `docker compose up -d`. The only way to wipe them is to run `docker compose down -v`, which explicitly removes volumes. Be careful with that command — it deletes your ingested data and your downloaded models.

---

## 7. Startup Sequencing vs Readiness

`depends_on` in `docker-compose.yml` controls the order in which Docker starts containers. It does not wait for a service to be fully ready before starting the next one.

This distinction matters because a container can be "Up" while the service inside is still initializing. Weaviate might be running but still loading its index. Ollama might be running but still pulling a model on first request. The ingestion API might start before Weaviate is ready to accept connections.

That is why this repo uses healthchecks alongside `depends_on`. Healthchecks define what "ready" actually means for each service, using real HTTP requests rather than just checking whether the process started. The `condition: service_healthy` option in `depends_on` tells Docker to wait until the healthcheck passes before starting the dependent service.

If you see a container that is "Up" but requests are failing, the service may still be initializing. Check the logs and wait a moment before assuming something is broken.

---

## 8. Resource Limits and Performance

All services in this repo have `mem_limit` set. On student machines, uncontrolled containers can consume all available RAM, causing the OS to kill processes or making the system unstable. Memory limits give each service a soft boundary.

The limits are set conservatively. If you are running the full stack (Weaviate, Ollama, ingestion-api, NGINX, Gradio) on a machine with limited RAM, the most likely bottleneck is Ollama, since it loads the language model into memory.

Common symptoms of memory pressure:
- The embeddings calls time out or return errors
- Chat responses are very slow
- A container restarts unexpectedly (the OS killed it)

To monitor memory usage in real time:
```bash
docker stats
```

To check logs for a specific container:
```bash
docker logs --tail 200 <container-name>
```

---

## 9. Logging and Observability

When a request fails, the key skill is knowing which layer to look at first. The request path goes: your client (browser or curl) → NGINX → ingestion-api → Weaviate and Ollama. The error message you see tells you where the chain broke.

**Common error patterns and what they mean:**

- `502 Bad Gateway` — NGINX cannot reach ingestion-api, or ingestion-api crashed. Check ingestion-api logs first.
- `401 or 403` — API key issue at NGINX. Check that you are passing `X-API-Key` correctly.
- `Timeout` — a slow upstream. On first run, Ollama may take several minutes to load a model. Subsequent requests will be faster.
- `Empty results from retrieval` — Weaviate class exists but has no objects, or the class name in your environment variables does not match what was created.
- `GraphQL errors` — usually a schema mismatch. The property name in the query doesn't match what was defined when the class was created.

**Useful log commands:**
```bash
docker logs --tail 200 edge-nginx
docker logs --tail 200 ingestion-api
docker logs --tail 200 weaviate
docker logs --tail 200 ollama
```

---

## 10. Practical Commands for Day-to-Day Work

**Start and stop the full stack:**
```bash
docker compose up -d
docker compose down
```

**Rebuild a single service after code changes:**
```bash
docker compose up -d --build ingestion-api
docker compose up -d --build gradio-ui
```

**Check what is running:**
```bash
docker ps
```

**Open a shell inside a container:**
```bash
docker exec -it ingestion-api sh
docker exec -it edge-nginx sh
```

**Verify internal connectivity from inside the network:**
```bash
docker exec -i ingestion-api python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://weaviate:8080/v1/.well-known/ready").read().decode())
PY
```

**Check Weaviate class list from inside the network:**
```bash
docker exec -i ingestion-api python - <<'PY'
import urllib.request, json
data = json.loads(urllib.request.urlopen("http://weaviate:8080/v1/schema").read())
for c in data.get("classes", []):
    print(c["class"])
PY
```

---

## 11. Debugging Failure Modes Methodically

This section is written as "if you see X, check Y."

### 502 Bad Gateway from NGINX

NGINX cannot get a valid response from ingestion-api. Work through this checklist in order:

1. Check whether ingestion-api is running: `docker ps --filter "name=ingestion-api"`
2. Check whether NGINX can reach it: `docker exec -i edge-nginx wget -qO- http://ingestion-api:8000/health || echo "failed"`
3. Check ingestion-api logs for crashes: `docker logs --tail 200 ingestion-api`

Common causes: an `ImportError` from a code change, a `SyntaxError`, or an environment variable that fails to parse on startup.

### Empty results or GraphQL errors from Weaviate

Weaviate does not have that class, or the class name doesn't match. Either it was never created, the class name in your environment variables does not match what exists in Weaviate, or you wiped volumes and did not re-ingest.

List existing classes:
```bash
curl -sS http://localhost:8080/v1/schema | python -m json.tool
```

Check object count:
```bash
curl -sS -X POST http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ Aggregate { LabDoc { meta { count } } } }"}' \
  | python -m json.tool
```

If the class is missing, re-run ingestion. If the name is wrong, check `WEAVIATE_CLASS` in your `.env` file.

### Gradio UI times out

The UI client gave up waiting for a response. Common causes: Ollama is loading a model on first request (this can take several minutes), embedding calls are slow, or the prompt being sent to Ollama is very large.

Check Ollama logs to see if it is still loading:
```bash
docker logs --tail 50 ollama
```

If this is the first request after startup, wait a few minutes and try again.

### Weaviate shows as unhealthy but responds to requests

The Compose healthcheck may be too strict or not matching real behavior. Weaviate exposes two readiness endpoints:
- `GET /v1/.well-known/ready` — returns `200` when Weaviate is ready
- `GET /v1/.well-known/live` — returns `200` when the process is alive

Prefer the `ready` endpoint in healthchecks.

### Embedding / Ollama connection errors

If your ingestion API is configured with `OLLAMA_BASE_URL` pointing to a service that does not exist in your Compose file, embedding calls will fail silently or with connection errors. Verify the service name in your environment variables matches the service name in `docker-compose.yml`.

```bash
docker exec -i ingestion-api python - <<'PY'
import os, urllib.request
base = os.getenv("OLLAMA_BASE_URL", "")
print("OLLAMA_BASE_URL =", base)
print("status =", urllib.request.urlopen(f"{base}/api/tags").status)
PY
```

---

## 12. Security Rationale: Boundaries, Secrets, and Exposure Control

This repo makes specific choices to teach production-like security habits.

### One exposed front door

Only NGINX is exposed on a host port. Everything else — Weaviate, Ollama, the ingestion API — is on the internal network. This reduces the risk of accidentally exposing a database to the internet and forces all traffic through a single authenticated gateway.

The exception in this repo is that the Weaviate port 8080 is published for debugging and direct inspection. In a real deployment, that would be removed.

### Secrets live in .env

API keys and configuration values that vary by machine or student are kept in a `.env` file that is not committed to the repo. The `.env.example` file shows students what variables are needed without exposing real values.

If you hardcode secrets in Python files or Dockerfiles and commit them, they become part of the git history permanently — even if you delete them later. Use environment variables.

---

## 13. Appendix: Tracing a Request End-to-End

This is the most useful debugging exercise you can do. Run through these steps in order to verify every layer of the system is working.

### Step A: Verify the gateway is alive

```bash
curl -i http://localhost:8088/proxy-health
```
Expected: `HTTP 200` with body `ok`. If this fails, NGINX is not running or not reachable.

### Step B: Verify the API through the gateway

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i http://localhost:8088/health -H "X-API-Key: $EDGE_API_KEY"
```
Expected: `HTTP 200` with JSON like `{"ok":true,"uptime_s":123}`. If this fails, the API key may be wrong or ingestion-api is down.

### Step C: Verify Weaviate

```bash
curl -sS http://localhost:8080/v1/.well-known/ready
```
Expected: `{}` with HTTP 200. If this fails, Weaviate is not running or still initializing.

Check that the schema was created:
```bash
curl -sS http://localhost:8080/v1/schema | python -m json.tool
```

### Step D: Verify Ollama reachability from inside the network

```bash
docker exec -i ingestion-api python - <<'PY'
import os, urllib.request
base = os.getenv("OLLAMA_BASE_URL", "")
print("OLLAMA_BASE_URL =", base)
print("status =", urllib.request.urlopen(f"{base}/api/tags").status)
PY
```
Expected: `status 200`. If this fails, Ollama is not reachable from inside the ingestion-api container.

### Step E: Ingest a document and retrieve it

**Ingest:**
```bash
curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Smoke Test Doc",
    "url": "https://example.com/smoke-test",
    "source": "smoke-test",
    "published_date": "2026-01-01",
    "text": "This document exists to verify ingestion, embedding, storage, and retrieval work end-to-end."
  }'
```

**Retrieve:**
```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=verify ingestion embedding retrieval" | python -m json.tool
```

If retrieval returns results, the full pipeline is working. If it returns empty results, check the Weaviate schema and object count, then work through the checklist in Section 11.

**Verify directly in Weaviate:**
```bash
curl -sS -X POST http://localhost:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ Aggregate { LabDoc { meta { count } } } }"}' \
  | python -m json.tool
```

A `count` greater than zero confirms objects were stored successfully.

---

## Closing Note

The architecture in this repo is not Docker for its own sake. It exists to give you a realistic, debuggable system where each layer has a clear responsibility and a clear interface.

Once you can trace a request end-to-end and reason about which layer is responsible for which failure, you have the mental model needed to modify the system safely and confidently.
