# Lesson 8 — Gradio Chat UI: Talking to Your Weaviate RAG Bot

## Learning objectives

By the end of this lesson, you will be able to:

- Open the chat UI and use it like an end-user.
- Explain the request path: **UI → NGINX → FastAPI → Weaviate/Ollama → UI**.
- Interpret the **sources** returned with each answer (why they matter).
- Know what to check when the UI shows an error (debugging order).

---

## Step 1 — Open the UI

Open in a new tab:

- http://localhost:7860

If the page does not load:

```bash
./bin/status.sh
docker compose logs gradio-ui --tail=200
```

---

## Step 2 — Ingest the cybersecurity dataset

If you haven’t ingested yet, do it now:

```bash
./bin/ingest_sample.sh
```

This ingests `data/sample_articles.jsonl`.

---

## Step 3 — Use the chatbot (prompts that match the dataset)

Try:

- “What is the difference between authentication and authorization?”
- “Why is exposing a database directly to the internet risky?”
- “What should we log during an incident and why?”
- “What is supply chain risk in AI pipelines?”

You should see:

1) an answer (may take 60-140s) 
2) a **Sources** section listing retrieved documents

---

## Step 4 — What the “Sources” section means

This is a **RAG** bot (Retrieval-Augmented Generation):

- it retrieves relevant docs from Weaviate
- then it asks the LLM (Ollama) to answer using those docs
- it returns the answer **and** the sources

Why sources matter:

- they make answers more trustworthy
- they show what information the model used
- they help you detect hallucinations or missing coverage

---

## Step 5 — Debugging order when something fails

When chat fails, check in this order:

### 5.1 Proxy up?

```bash
curl -i http://localhost:8088/proxy-health
```

### 5.2 API up and auth works?

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health
```

### 5.3 Is Ollama running?

```bash
docker compose ps ollama
docker compose logs ollama --tail=100
```

If needed, pull the model again:

```bash
./bin/pull_model.sh
```

---

## Checkpoints

- UI loads at `http://localhost:7860`
- You can ask at least 3 cybersecurity questions and get answers
- Each answer includes a Sources section
- You can explain the request path in one sentence

[Lesson 9](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/09-operations-testing-and-troubleshooting.md)
