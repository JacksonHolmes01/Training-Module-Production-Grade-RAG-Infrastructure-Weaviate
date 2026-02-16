# Lesson 3 — Docker Compose Architecture & Resource Limits (8 GB Caps)

## Learning objectives

By the end of this lesson, you will be able to:

- Read the `docker-compose.yml` file and understand the purpose of each major section.
- Explain how Docker networking works in this lab (service-name DNS + internal network).
- Explain what Docker volumes do and what data persists across restarts.
- Explain why we enforce memory limits (and how to adjust them safely if needed).

---

## Step 1 — Open and read `docker-compose.yml`

Open `docker-compose.yml` in a text editor and skim the structure.

You will see:

- `services:` — each container we run
- `networks:` — how containers talk to each other
- `volumes:` — what data persists

---

## Step 2 — Understand each service

### Weaviate

In `docker-compose.yml`, find the `weaviate:` service.

Key things to notice:

- `mem_limit: 8g` (resource boundary)
- it is on `networks: internal`
- it uses the `weaviate_data` volume

### text2vec-transformers

This service provides embeddings.

Key things to notice:

- Weaviate calls it using `TRANSFORMERS_INFERENCE_API=http://text2vec-transformers:8080`
- it is internal-only

### Ollama

This is the local LLM runtime.

Key things to notice:

- `mem_limit: 8g`
- it uses a volume called `ollama_data` to store models

### ingestion-api

FastAPI service built from local code in `ingestion-api/`.

Key things to notice:

- it reads environment from `.env`
- it depends on Weaviate, transformer module, and Ollama
- it has a `/health` endpoint and a healthcheck in Compose

### nginx

Edge proxy that enforces API key auth.

Key things to notice:

- exposes port `8088` to the host
- uses an NGINX config template where `${EDGE_API_KEY}` is injected

### gradio-ui

Chat UI for students.

Key things to notice:

- exposes port `7860` to the host
- talks to the API through nginx
- is given `EDGE_API_KEY` via environment so it can call protected endpoints

---

## Step 3 — Networking: how containers talk to each other

All services are connected to the Docker network called:

- `internal`

In Docker, service names become DNS names.

That means:

- The API can call Weaviate at `http://weaviate:8080`
- Weaviate can call transformers at `http://text2vec-transformers:8080`
- The API can call Ollama at `http://ollama:11434`
- The UI calls the API through `http://nginx:8088`

### Why internal networking matters

Because it means:

- internal services are not accessible from your laptop directly
- you reduce attack surface
- you force all external access through controlled entrypoints (NGINX + API)

---

## Step 4 — Volumes: what persists (and why)

Volumes store data outside a container’s writable layer, so data survives:

- container restarts
- container rebuilds
- `docker compose down` (unless you delete volumes)

This lab uses:

- `weaviate_data` — your stored objects + vectors
- `ollama_data` — downloaded models

### Practical implication

If you pull a model once, it stays on disk.

If you want a clean wipe, use the reset script (Lesson 9).

---

## Step 5 — Memory limits (Weaviate + Ollama capped at 8 GB)

### What the lab enforces

- Weaviate: `mem_limit: 8g`
- Ollama: `mem_limit: 8g`

### Why we enforce limits 

If you don’t limit resources:

- a container can consume memory freely
- your machine may slow to a crawl
- the OS may kill random processes
- debugging becomes unpredictable

Resource limits are part of real deployments — you must plan capacity.

### Important note: Docker Desktop has its own limit

On Mac/Windows, Docker Desktop has an overall memory cap.

If Docker Desktop only has 8 GB total, two containers allowed 8 GB each will compete.

If you see performance issues:

1. Use a smaller model (recommended)
2. Increase Docker Desktop memory settings (if possible)
3. Lower container caps and document what you changed

---

## Step 6 — How to adjust limits if needed 

## Optional: Reducing Memory Usage (If Your Machine Struggles)

If your laptop becomes slow, Docker containers restart unexpectedly, or generation hangs, your system may be running out of RAM.

In this lab, several services have memory limits defined in `docker-compose.yml`. You can safely lower these if needed.

---

## Step 1 — Open `docker-compose.yml`

You need to edit:

```
docker-compose.yml
```

### Option A — Using a Code Editor

1. Open your project folder.
2. Click on `docker-compose.yml` in the root directory.
3. Scroll to the service you want to modify (for example, `ollama`).

### Option B — Using the Terminal (Nano)

From your project root directory:

```bash
nano docker-compose.yml
```

Use arrow keys to navigate.  
Press `Ctrl + O` to save.  
Press `Enter` to confirm.  
Press `Ctrl + X` to exit.

---

## Step 2 — Reduce the Memory Limit

Locate the service block. For example:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: ollama
  restart: unless-stopped
  mem_limit: 8g
```

To reduce memory usage, change:

```yaml
mem_limit: 8g
```

to:

```yaml
mem_limit: 4g
```

You can apply the same idea to other services if necessary:

- `weaviate`
- `text2vec-transformers`
- `ingestion-api`

Do not reduce memory too aggressively.  
Ollama especially needs enough RAM to load the model.

---

## Step 3 — Apply the Changes

After saving the file, you must recreate the containers:

```bash
docker compose down
docker compose up -d --build
```

This ensures the new memory limits take effect.

---

## Step 4 — Verify It Worked

Run:

```bash
docker stats
```

You should now see lower memory limits for the adjusted containers.

---

## When Should You Do This?

Reduce memory limits if:

- Your fan is constantly running
- The system becomes unresponsive
- Containers restart automatically
- You see OOM (Out Of Memory) errors

If everything is running smoothly, you do not need to change this.

---

## Quick “verification” commands

See your running services:

```bash
docker compose ps
```

View memory usage:

```bash
docker stats
```

---

## Checkpoints 

- You can explain why most services are internal-only.
- You can explain what the volumes store and why they matter.
- You can point to where the 8 GB limits are set for Weaviate and Ollama.
- You can explain what `docker stats` shows in one sentence.

[Lesson 4](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/33047948ed1267f174341f67ffb8f102a9b3a1f2/lessons/04-edge-auth-with-nginx.md)
