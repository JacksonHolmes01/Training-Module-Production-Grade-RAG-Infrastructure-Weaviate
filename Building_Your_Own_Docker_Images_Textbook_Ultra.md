# Building Your Own Docker Images (Textbook-Style + Step-by-Step Labs)

This document teaches you **how to create Docker images**, not just what they are. It is meant to be read like a chapter of a textbook, and then followed like a lab manual.

---

## Table of Contents

1. Images vs containers (the exact difference)
2. How Docker builds images (layers, cache, and reproducibility)
3. Anatomy of a Dockerfile (each instruction explained)
4. Choosing a base image (security and size trade-offs)
5. Python/FastAPI lab: build an API image step-by-step
6. Designing for fast rebuilds (cache best practices)
7. Multi-stage builds (why they matter)
8. Environment variables, `.env`, and secrets (what belongs where)
9. Exposing ports and binding addresses (why `0.0.0.0` matters)
10. Healthchecks and readiness (why “running” is not “ready”)
11. Tagging, naming, and versioning images
12. Debugging broken builds (common errors + fixes)
13. Publishing images (optional): Docker Hub / GHCR
14. Hardening checklist: non-root users, pinning, scanning

---

# 1. Images vs Containers 

- **Image**: a read-only blueprint (filesystem + metadata)
- **Container**: a running instance of an image (a process using that filesystem)

A useful mental model:
- Image = frozen recipe
- Container = the meal you cooked from that recipe

When you run:
```bash
docker run nginx:1.27-alpine
```
Docker:
1) downloads the image (if you don’t have it)
2) creates a container from it
3) starts the main process

---

# 2. How Docker Builds Images: Layers and Caching

## 2.1 Every Dockerfile instruction becomes a layer (usually)
Docker builds images one step at a time. Each step produces a **layer**.
Layers are cached, so future builds are faster if earlier layers did not change.

Example:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "app"]
```

If you change only your app code:
- Docker can reuse cached layers up through `pip install`
- and only redo `COPY . .`

## 2.2 Why caching is one of the main skills
Being “good at Docker” often means:
- structuring a Dockerfile so rebuilds are fast
- knowing which edits invalidate cache

---

# 3. Anatomy of a Dockerfile (Every Instruction Explained)

## `FROM`
Chooses the base image:
- sets your starting filesystem
- sets the OS libraries you inherit

## `WORKDIR`
Sets the working directory inside the container:
- creates the folder if it does not exist
- avoids writing `cd /app` in commands

## `COPY`
Copies files from your computer into the image.

Use `COPY` by default because it is explicit.

## `RUN`
Runs a command at build time, producing a new layer.
Typical uses:
- install dependencies
- compile code
- create users

## `ENV`
Sets environment variables inside the image.

## `EXPOSE`
Documents which port the container listens on.
Important: it does **not** publish a port to your host.

Publishing happens with:
- `docker run -p ...`
- Compose `ports:`

## `CMD` vs `ENTRYPOINT`
- `CMD` is the default command (easy to override)
- `ENTRYPOINT` is “always run this” (harder to override)

---

# 4. Choosing a Base Image: Security and Size Trade-Offs

## 4.1 Common base options for Python
- `python:3.11-slim` (good default for teaching)
- `python:3.11-alpine` (small, but can cause dependency pain)
- `debian:bookworm-slim` + manual Python install (advanced)

## 4.2 Why size matters
Smaller images:
- pull faster
- build faster in CI
- have fewer packages to exploit (smaller attack surface)

But smaller images sometimes require more manual installs for native dependencies.

---

# 5. Lab: Build a FastAPI Image Step-by-Step

This is a guided lab. You will build a container image for a FastAPI app (the same pattern used by the `ingestion-api` service in this repo).

## 5.1 Create a minimal FastAPI project
Folder structure:
```
my-api/
  app/
    main.py
  requirements.txt
  Dockerfile
```

Create `app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}
```

Create `requirements.txt`:
```
fastapi==0.110.0
uvicorn[standard]==0.27.1
```

## 5.2 Write the Dockerfile (recommended version)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

# 1) runtime settings (best practice)
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

# 2) set workdir
WORKDIR /app

# 3) dependency install (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) copy app code last (preserves cache when code changes)
COPY app ./app

# 5) start server
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Why `--host 0.0.0.0` matters
Inside a container:
- `127.0.0.1` means “only inside the container”
- `0.0.0.0` means “listen on the container network interface”

If you bind to `127.0.0.1`, your host may not be able to reach the port even if you publish it.

## 5.3 Build the image
From inside `my-api/`:
```bash
docker build -t my-api:dev .
```

## 5.4 Run the container
```bash
docker run --rm -p 8000:8000 my-api:dev
```

Test:
```bash
curl -sS http://localhost:8000/health
```

Expected:
```json
{"ok": true}
```

---

# 6. Designing for Fast Rebuilds (Cache Best Practices)

## 6.1 The golden rule
Copy dependency files first, install, then copy code.

Good:
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Bad (slow rebuilds):
```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

Because changing any file forces Docker to re-run everything after that line.

## 6.2 `.dockerignore` (the file people forget)
A `.dockerignore` prevents junk files from being copied into the build context:
- `.git/`
- `__pycache__/`
- `node_modules/`
- large datasets

Example `.dockerignore`:
```
.git
__pycache__
*.pyc
node_modules
data
```

---

# 7. Multi-Stage Builds 

Multi-stage builds let you:
- compile in a “builder” image that has gcc/build deps
- copy only final artifacts into a smaller runtime image

This is huge for:
- Node frontends
- compiled Python deps
- Go/Rust apps

Example:
```dockerfile
FROM node:20 AS build
WORKDIR /src
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
```

---

# 8. Environment Variables, `.env`, and Secrets

## 8.1 What belongs in `.env`
- model names (`OLLAMA_MODEL`)
- base URLs (`OLLAMA_BASE_URL`)
- API keys for local testing

## 8.2 What should not be baked into an image
Do not hardcode secrets in:
- Dockerfile `ENV`
- committed config files
- source code

Instead, pass them at runtime:
- `docker run -e KEY=value ...`
- Compose `env_file: .env`

---

# 9. Healthchecks and Readiness

A container can be “running” but not ready. Examples:
- a DB is still initializing
- a model is still loading into memory

A good healthcheck:
- runs fast (1–3 seconds)
- hits a lightweight endpoint

Example (Compose):
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
  interval: 10s
  timeout: 5s
  retries: 20
```

---

# 10. Tagging and Versioning Images

An image name has:
- repository name
- tag

Examples:
- `my-api:dev`
- `my-api:v1.0.0`
- `my-org/my-api:2026-02-19`

Production best practice:
- use immutable tags (version or git SHA)
- avoid relying on `latest`

---

# 11. Debugging Broken Builds (Common Errors)

## “Module not found”
Your code may not be copied into the image.
Fix:
- verify `COPY app ./app`
- verify imports match your folder structure

## “Port works in container but not from host”
Usually you bound to localhost inside the container.
Fix:
- ensure uvicorn uses `--host 0.0.0.0`

## “pip install fails”
You may need system libraries for native builds.
Fix:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential     && rm -rf /var/lib/apt/lists/*
```

---

# 12. Publishing Images (Optional)

## Docker Hub
1) `docker login`
2) tag:
```bash
docker tag my-api:dev yourname/my-api:dev
```
3) push:
```bash
docker push yourname/my-api:dev
```

## GitHub Container Registry (GHCR)
Tag as `ghcr.io/<user>/<image>:<tag>` and push (requires a token).

---

# 13. Hardening Checklist

- Pin base images (avoid floating tags)
- Run as non-root user
- Use minimal packages
- Scan images (Trivy, Docker Scout)
- Keep secrets out of images

Example non-root pattern:
```dockerfile
RUN useradd -m appuser
USER appuser
```

---

## Closing mental model
When you can answer these questions, you understand Docker images:

1) What files ended up inside my image?
2) Which process runs when my container starts?
3) Where do my logs go?
4) Which ports are exposed to the host?
5) Which data persists across restarts?
6) How do environment variables reach my code?
