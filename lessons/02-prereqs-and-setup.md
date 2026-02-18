# Lesson 2 — Prereqs & Setup: Docker, Secrets, and First Boot

## Learning objectives

By the end of this lesson, you will be able to:

- Verify your machine has Docker and Docker Compose installed and working.
- Create a `.env` file safely and explain why you should not commit secrets.
- Build and start the lab stack with Docker Compose.
- Confirm each container is running and diagnose basic startup issues using logs.

---

## Step 0 — What you need before you start

### Required tools

You need:

- **Docker** (Docker Desktop on Mac/Windows, Docker Engine + Compose on Linux)
- A terminal (macOS Terminal, Windows PowerShell, etc.)
- Internet access (first run must pull container images)

### Recommended system specs

Because we are running both Weaviate and an LLM runtime:

- **16 GB RAM** is recommended
- **10+ GB free disk** is recommended (models can be large)
- If your machine is smaller, you can still do the lab by using a **small Ollama model** (we will show how).

---

## Step 1 — Verify Docker is installed

Run these commands:

```bash
docker --version
docker compose version
```

### What “good output” looks like

You should see version numbers, for example:

- `Docker version 25.x.x`
- `Docker Compose version v2.x.x`

If you see “command not found,” install Docker first.

[Install Docker](https://docs.docker.com/get-docker/)

---

## Step 2 — Download the lab repo and enter the folder

If you cloned from GitHub:

```bash
git clone <YOUR-LAB-2-REPO-URL>
cd Training-Module-Production-Grade-RAG-Infrastructure-Weviate
```

Confirm you’re in the correct folder:

```bash
ls
```

You should see files like:
- `docker-compose.yml`
- `.env.example`
- `lessons/`
- `bin/`

---

## Step 3 — Create your `.env` file (secrets)

This lab uses a `.env` file for configuration, including your API key.

Create it from the example:

```bash
cp .env.example .env
```

### Why we use `.env`

- It keeps secrets out of your code.
- It makes the lab configurable without editing many files.
- `.env` is in `.gitignore`, meaning it will not be committed to GitHub.

### Set a real API key (important)

Open `.env` and change this:

## Editing the `.env` File with Nano

To edit your environment configuration file, use the Nano text editor.

From the root of the project directory, run:

```bash
nano .env
```

- `EDGE_API_KEY=change-me-to-a-long-random-string`

Make it a long random value.

Generate one quickly:

```bash
python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
```

Paste the output into `.env`.

### Save the File in Nano

After making your changes:

1. Press `Ctrl + O` (hold Control and press the letter **O**)  
   - Nano will show: `File Name to Write: .env`

2. Press `Enter` to confirm and save.

You should see a message at the bottom confirming that the file was written.

---

## Step 4 — Start the stack

Run:

```bash
docker compose up -d --build
```

### What this command does

- `up` starts services
- `-d` runs them in the background (so your terminal is free)
- `--build` rebuilds images for services that use your local code (FastAPI + Gradio)

### First start can take a few minutes

The first run pulls images and builds containers.
That can take longer than future runs.

---

## Step 5 — Check status (is everything running?)

Run:

```bash
./bin/status.sh
```

You should see services like:
- `weaviate`
- `text2vec-transformers`
- `ollama`
- `ingestion-api`
- `edge-nginx`
- `gradio-ui`

### If something is not running

Look at logs:

```bash
docker compose logs --tail=200
```

Or logs for one service:

```bash
docker compose logs ingestion-api --tail=200
```

Logs are your best debugging tool. Don’t guess — check logs.

---

## Step 6 — Confirm the UI loads

Open your browser:

- http://localhost:7860

You should see a chat interface and a system status panel.

If the UI loads but chat fails, that is normal before you pull an Ollama model (Lesson 7).

---

## Common issues & fixes

- **Port already in use (7860 or 8088)**  
  Another process is using that port. Either stop it or change the port mapping in `docker-compose.yml`.

- **Docker Desktop memory too low**  
  Docker Desktop has a memory setting. If Docker only has 8 GB total and services are capped at 8 GB each, performance will suffer. Increase Docker Desktop memory if possible.

- **UI loads but chat fails**  
  Usually means no Ollama model is installed yet. Continue to Lesson 7 and run `./bin/pull_model.sh`.

---

## Checkpoints 

- `docker compose up -d --build` completes without errors.
- `./bin/status.sh` shows services running (some may take time to become ready).
- You can open `http://localhost:7860` and see the Gradio UI.

[Lesson 3](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/03-compose-architecture-and-resource-limits.md)
