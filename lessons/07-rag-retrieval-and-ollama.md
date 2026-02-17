# Lesson 7 — RAG: Retrieval + Ollama Generation (and Debugging Each Step)

## Learning objectives

By the end of this lesson, you will be able to:

- Describe the RAG pipeline used in this lab (retrieval + generation).
- Pull and manage an Ollama model.
- Separate **retrieval problems** from **generation problems** using debug endpoints.
- Inspect the exact prompt sent to the LLM and explain how grounding works.
- Tune a simple RAG parameter (`RAG_TOP_K`) and observe how outputs change.

---

## Step 0 — Make sure you ingested data

If your database is empty, retrieval will be empty.

If you haven’t done Lesson 6, do:

```bash
./bin/ingest_sample.sh
```

---

## Step 1 — Pull the Ollama Model (Required)

This lab expects you to use the same lightweight model used throughout the lessons to avoid slow generation or memory issues.

We recommend:

- `llama3.2:1b`

This model is fast, stable, and appropriate for laptops with limited RAM.

---

### 1.1 Set the Model in `.env`

Open your `.env` file and confirm:

```
OLLAMA_MODEL=llama3.2:1b
```

If you need to edit it using Nano:

```bash
nano .env
```

Save with:

- `Ctrl + O` → Enter  
- `Ctrl + X`

---

### 1.2 Pull the Model

Pull whatever model is currently set in `.env`:

```bash
./bin/pull_model.sh
```

You should see Ollama download output and then completion.

---

### 1.3 Verify the Model Exists

```bash
docker exec -it ollama ollama list
```

Expected output should include:

```
llama3.2:1b
```

If you previously pulled a larger model (e.g., 8B) and want to remove it:

```bash
docker exec -it ollama ollama rm llama3.1:8b
```

---

### If Generation Is Slow

If `/chat` takes more than ~60–120 seconds on a laptop:

- Confirm you are using `llama3.2:1b`
- Restart Ollama:

```bash
docker compose restart ollama
```

- Then test generation directly:

```bash
curl -sS -X POST "http://localhost:8088/debug/ollama" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain the CIA triad in 2 sentences."}'
```

If this returns quickly, your model is correctly configured.

## Step 2 — Understand the RAG pipeline in this repo

When you hit `/chat`:

1. API calls Weaviate GraphQL with `nearText`
2. API collects top `K` docs and truncates each to a short snippet
3. API builds a prompt that includes snippets and a rule: “Use only sources”
4. API calls Ollama `/api/generate`
5. API returns answer + sources

# Note

When you hit `/chat`, you are calling an HTTP API endpoint.  
You do **not** type `/chat` into your terminal by itself.

`/chat` only responds when you send an HTTP request to it (for example with `curl`, the Gradio UI, or a browser client).

---

### 2.1 What “hit `/chat`” actually means

This is a valid way to call `/chat` from your terminal:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -i --max-time 60 \
  -H "X-API-Key: $EDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the CIA triad? Answer in 2 sentences."}' \
  http://localhost:8088/chat
```

## 2.2 What Happens Inside the Pipeline

When `/chat` receives a request, the system executes these steps:

### 1. NGINX (Edge Layer)

- Receives the HTTP request on port `8088`
- Verifies the `X-API-Key`
- Blocks unauthorized traffic
- Forwards valid requests to the internal FastAPI service

This prevents direct access to the API container.

---

### 2. FastAPI (Application Layer)

- Verifies the API key again (defense in depth)
- Validates the request schema (`ChatIn`)
- Begins the RAG workflow

This is where orchestration happens.

---

### 3. Weaviate (Retrieval Layer)

- Receives a semantic search query
- Uses vector embeddings to find meaning-based matches
- Returns the top-K most relevant documents

This step answers:
> “What stored knowledge is relevant to this question?”

---

### 4. Prompt Construction

The API builds a structured prompt containing:

- The user’s question
- Retrieved source excerpts
- Instructions to use only those sources

This is the **grounding mechanism** that prevents hallucination.

---

### 5. Ollama (Generation Layer)

- Receives the fully constructed prompt
- Runs the local LLM (e.g., `llama3.2:1b`)
- Generates a grounded answer
- Returns the completion to the API

This step transforms context into natural language output.

---

### 6. Response Returned to the User

The API responds with:

- `answer` — the generated response
- `sources` — the retrieved documents used to ground the answer

The client (curl or Gradio UI) displays the result.

---

## Step 3 — Debug retrieval first (no LLM)

RAG has two major phases:

1. Retrieval (Weaviate)
2. Generation (Ollama)

If retrieval fails, generation will either:
- hallucinate
- return weak answers
- hang while waiting
- or fail entirely

Always prove retrieval works first.

---

### Run Retrieval Directly (No LLM Involved)

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=What is defense in depth and how does this lab demonstrate it?" | python -m json.tool
```
If `sources` is empty:

- Do NOT debug Ollama
- Do NOT modify generation settings
- Fix ingestion / vectorizer / Weaviate first

Go back to:

- **Lesson 3 — Docker & Service Health**  
  (verify Weaviate and text2vec-transformers readiness)

- **Lesson 4 — Ingestion & Validation**  
  (re-run ingestion and confirm documents exist)

- **Lesson 5 — Weaviate Schema & Vectorization**  
  (confirm schema matches your request model)

Only move to generation debugging after retrieval is confirmed healthy.

---

## Step 4 — Inspect the Prompt (Understand What the LLM Actually Sees)

The LLM does **not** see your database.  
It does **not** see your schema.  
It does **not** see your retrieval logic.

It only sees a **single string of text** — the prompt you construct.

The `/debug/prompt` endpoint allows you to inspect that exact string.

---

## What This Endpoint Does

When you call `/debug/prompt`, the system:

1. Authenticates the request (NGINX + FastAPI API key check)
2. Calls `retrieve_sources()`  
   - Queries Weaviate using semantic search  
   - Retrieves top-K documents  
3. Calls `build_prompt()`  
   - Formats the user question  
   - Inserts the retrieved sources  
   - Adds grounding instructions  
4. Returns the full prompt **without calling Ollama**

This isolates prompt construction from generation.

---

## What Happens Internally

```
User → NGINX (API key check)
     → FastAPI /debug/prompt
         → retrieve_sources()
             → Weaviate GraphQL query
         → build_prompt()
             → Insert question
             → Insert source blocks
             → Add grounding rules
         → Return prompt as JSON
```

No LLM is called during this step.

---

## Run the Prompt Inspection

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "Why is it risky to expose a vector database directly to the internet?" }' \
  | python -m json.tool
```

---

## What You Should See

Inside the JSON response:

- `"prompt"` → a long formatted string
- `"sources"` → structured retrieval results
- `"prompt_chars"` → prompt size (important for model limits)

---

## What to Look For in the Prompt

Carefully inspect the `"prompt"` field.

You should see:

### 1. Clear Instruction Block

```
You are a helpful assistant answering questions using ONLY the provided sources.
If the sources are insufficient, say that clearly and suggest what information to add.
```

This is your grounding enforcement.

---

### 2. User Question Section

```
User question:
Why is it risky to expose a vector database directly to the internet?
```

If this is missing, your prompt builder is broken.

## How to Fix It (If your prompt builder is not broken skip this step)

### 1. Open the Prompt Builder File

Using a code editor:
- Open `ingestion-api/app/rag.py`
- Locate the `build_prompt()` function.

Using Nano (terminal):

```bash
nano ingestion-api/app/rag.py
```

---

### 2. Verify `build_prompt()` Is Structurally Correct

Inside `build_prompt()`, confirm that it:

- Accepts both `user_question` and `sources`
- Builds a `Sources:` section
- Iterates over sources using something like:
  ```python
  for i, s in enumerate(sources, start=1):
  ```
- Inserts clearly labeled blocks like:
  ```
  [Source 1]
  [Source 2]
  ```
- Returns the entire formatted prompt string

You should see something structurally similar to:

```python
def build_prompt(user_question: str, sources: list[dict]) -> str:
    if not sources:
        context = "No sources retrieved."
    else:
        blocks = []
        for i, s in enumerate(sources, start=1):
            blocks.append(
                f"""[Source {i}]
Title: {s.get('title')}
URL: {s.get('url')}
Excerpt:
{s.get('snippet')}
"""
            )
        context = "\n\n".join(blocks)

    return f"""You are a helpful assistant answering questions using ONLY the provided sources.

User question:
{user_question}

Sources:
{context}

Instructions:
- Write a clear answer.
- Use only the provided sources.
"""
```

---

### 3. Rebuild the API

After saving changes:

```bash
docker compose up -d --build ingestion-api
```

---

### 4. Re-test Prompt Inspection

```bash
curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "Test question" }' | python -m json.tool
```

If the response now includes:

- A `Sources:` section  
- `[Source 1]`, `[Source 2]` blocks  
- Proper excerpts  

Then your prompt builder is fixed and RAG grounding will work correctly

---

## Step 3 — Understanding the Sources Section (Next Step)

This step is about verifying that retrieval is actually working before you ever involve the LLM.

Call:

```bash
curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "What is the CIA triad?" }' | python -m json.tool
```

---

## What Happens Internally During Step 3

When `/debug/prompt` runs, the following sequence happens:

1. Your question is received by FastAPI.
2. `retrieve_sources(query)` is called.
3. A GraphQL `nearText` query is sent to Weaviate.
4. Weaviate performs semantic search using stored embeddings.
5. Top-K documents are returned.
6. Snippets are extracted from each document.
7. The prompt builder formats them into structured `[Source X]` blocks.
8. The final prompt string is returned to you.

No LLM is involved yet.

This step isolates the retrieval + formatting layers only.

---

## What You Should See

Having successfully run the previous step you should see structured blocks like:

[Source 1]  
Title: CIA Triad: Confidentiality, Integrity, Availability  
URL: ...  
Excerpt:  
The CIA triad is a basic model...

You should see:

- Multiple `[Source X]` blocks  
- Real document content in the excerpts  
- Distances (if included in debug output)  
- A properly formatted prompt structure  

---

## How to Interpret What You See

### Case 1 — Multiple Strong Sources

This means:

- Your documents were ingested correctly.
- Embeddings were generated.
- Weaviate is functioning.
- Semantic search is working.

You can now trust retrieval.

---

### Case 2 — `sources: []` (Empty)

This means retrieval failed.

Common causes:

- Ingestion never happened.
- Schema is broken.
- Vectorizer container is down.
- Weaviate is not ready.
- The query is too vague.

What to do:

- Run `/debug/retrieve` directly.
- Check `docker compose logs weaviate`.
- Check `docker compose logs text2vec-transformers`.
- Confirm objects exist:
  
  docker exec -i ingestion-api python -c "import urllib.request; print(urllib.request.urlopen('http://weaviate:8080/v1/objects?class=LabDoc').read()[:300])"

Do not touch Ollama yet.

---

### Case 3 — Only One Weak or Irrelevant Source

Possible causes:

- Dataset too small  
- Query too generic  
- Embeddings not representative  
- Snippet length too short  

Possible fixes:

- Improve dataset  
- Improve document quality  
- Increase `RAG_TOP_K`  
- Increase `RAG_MAX_SOURCE_CHARS`  

---

### Case 4 — Snippets Look Truncated or Cut Off

This is controlled by:

RAG_MAX_SOURCE_CHARS

If excerpts are too short, the LLM may lack context.

You can increase the value in `.env`:

RAG_MAX_SOURCE_CHARS=2000

Then restart the ingestion API.

---

## Why Step 3 Is So Important

Many assume:

“Chat failed, so the model must be broken.”

In reality, most RAG failures happen before the LLM is even called.

Retrieval is the foundation.

If retrieval is wrong:

- The prompt will be wrong.  
- The answer will be wrong.  
- Debugging will be confusing.  

By validating Step 3 first, you confirm:

- The database layer works.  
- The embedding layer works.  
- The retrieval query works.  
- The formatting logic works.  

Only after this is correct should you debug generation.

---

## Step 4 — Call Full Chat (Retrieval + Generation)

This step runs your **entire RAG pipeline in production mode**. Unlike the debug endpoints, `/chat` executes all layers together:

1. NGINX validates the API key  
2. FastAPI validates the request body  
3. Weaviate performs semantic retrieval  
4. Your application builds a grounded prompt  
5. Ollama generates a response  
6. The API returns structured JSON  

If this works, your multi-service RAG architecture is functioning correctly.

---

### Run the Full Chat Request

```bash
curl -sS -X POST "http://localhost:8088/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{ "message": "What is defense in depth and how does this lab demonstrate it? Answer in 2 sentences." }' | python -m json.tool
```

---

## What Is Happening Internally

When this request runs:

- NGINX checks the `X-API-Key` before forwarding traffic  
- FastAPI validates the `ChatIn` schema  
- `retrieve_sources()` queries Weaviate via GraphQL  
- `build_prompt()` constructs a grounded instruction block with sources  
- `ollama_generate()` sends the prompt to Ollama  
- The API returns:

```json
{
  "answer": "...",
  "sources": [...]
}
```

This step may take longer than the debug endpoints because LLM generation consumes CPU and memory.

---

## Expected Output

You should see:

- An `"answer"` field containing a grounded explanation  
- A `"sources"` array listing the retrieved documents  

Example structure:

```json
{
  "answer": "Defense in depth is a layered security strategy that uses multiple controls to reduce risk. This lab demonstrates it by enforcing authentication at the edge with NGINX and again within the FastAPI application while keeping internal services isolated.",
  "sources": [
    {
      "title": "Defense in Depth: Layered Controls",
      "url": "https://example.org/cyber/defense-in-depth",
      "source": "Lab2-Cyber-Notes",
      "published_date": "2026-02-13",
      "distance": 0.78,
      "snippet": "Defense in depth means using multiple layers of security controls..."
    }
  ]
}
```

---

## If This Fails

- If `/debug/retrieve` works → retrieval is healthy  
- If `/debug/prompt` looks correct → prompt construction is healthy  
- If `/debug/ollama` works → model is healthy  

If all three succeed but `/chat` fails, the issue is orchestration (timeouts, async flow, or glue logic).

This step verifies that all layers operate together under real conditions.

## Step 5 — Tune RAG_TOP_K and observe changes (hands-on experiment)

`RAG_TOP_K` controls how many documents are retrieved.

1) Change `.env`:
```bash
RAG_TOP_K=2
```

2) Restart only the API (so it reloads env vars):
```bash
docker compose restart ingestion-api
```

3) Call debug retrieve again and observe fewer sources:
```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=Why do we use an API layer?" | python -m json.tool
```

4) Set `RAG_TOP_K=8`, restart API, and compare.

### What you learned

- More sources can increase coverage, but may also add noise.
- Fewer sources can be focused, but might miss key context.

This is a real RAG tradeoff.

---

## Troubleshooting 

- **Retrieval empty** → ingestion/vectorizer/Weaviate problem  
- **Retrieval works, chat fails** → Ollama/model problem  
- **Chat works but slow** → model too large or resource limits too tight  

Use logs to confirm:

```bash
docker compose logs ingestion-api --tail=200
docker compose logs ollama --tail=200
```

---

## Checkpoints

- You successfully pulled an Ollama model.
- `debug/retrieve` returns sources after ingestion.
- You can show the prompt from `debug/prompt` and explain grounding.
- You changed `RAG_TOP_K` and observed a measurable difference in outputs.

[Lesson 8](https://github.com/JacksonHolmes01/Training-Module-Production-Grade-RAG-Infrastructure-Weaviate/blob/main/lessons/08-gradio-chat-ui.md)
