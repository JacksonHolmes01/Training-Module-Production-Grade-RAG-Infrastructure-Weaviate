---

# Getting Started

## 1. Clone the repository

```bash
git clone <YOUR-REPO-URL>
cd Training-Module-Production-Grade-RAG-Infrastructure-Weaviate
```

## 2. Create your environment file

Copy the example environment file:

    cp .env.example .env

Open the newly created `.env` file in a text editor.

```bash
nano .env
```

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

To save:

1. Press **Control + X**
2. It will ask: `Save modified buffer?`
3. Press **Y**
4. Press **Enter**

Your file is now saved.


Important:
- Do NOT share this key.
- Do NOT commit your `.env` file to GitHub.
- Only the proxy and API need to know this value.

Once this is set, your system will require that key for any API request, which is how we enforce authentication at the edge.


## 3. Start the stack

```bash
docker compose up -d --build
```
---

# Common Issue: “Container name is already in use”

If you see this error when running `docker compose up`:

```
Error response from daemon: Conflict.
The container name "/weaviate" is already in use...
```

It means Docker already has a container named `weaviate` on your machine.

This usually happens if:

- You previously ran Lab 1 and did not stop it  
- You started this lab before and containers are still running  
- A previous Docker run did not shut down cleanly  

---

## How to Fix It

### Step 1 — Stop containers in this project

From inside the Lab 2 folder, run:

```bash
docker compose down
```

### Step 2 — If the error persists, remove the old container manually

```bash
docker rm -f weaviate
```

Then start the stack again:

```bash
docker compose up -d --build
```

---

## If You Still Have Lab 1 Running

If Lab 1 is still running, go into the Lab 1 folder and stop it:

```bash
cd <lab1-folder>
docker compose down
```

Then return to Lab 2 and start it again.

---

## Why This Happens

Docker does not allow two containers to have the same name.

Both Lab 1 and Lab 2 use the container name `weaviate`, so only one can run at a time.

You must stop one before starting the other.


## 4. Pull the model (one-time)

```bash
chmod +x bin/*.sh
```

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
