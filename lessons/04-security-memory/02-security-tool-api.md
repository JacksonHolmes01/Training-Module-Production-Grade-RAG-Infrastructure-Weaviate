# Lesson 4.2 — Expose Your Security Memory as an API Tool

**What you're building:** a small set of API endpoints that turn your `ExpandedVSCodeMemory` Weaviate class into something your IDE and AI assistant can actually call as a tool.

IDE stands for Integrated Development Environment — it's the application you write code in (VS Code, for example). IDEs can be extended with AI tools that call APIs like the one you're building here.

This is the step that bridges "we have a vector database full of security knowledge" to "my IDE can pull up the right standard and cite it while reviewing my code."

## Learning Outcomes

By the end of this lesson, you will:

- Add `/memory/health` and `/memory/query` endpoints to the FastAPI ingestion API
- Understand what a "retrieval tool contract" means and why the request/response shape matters
- (Optional) Connect memory retrieval results into your `/chat` pipeline

---

## 1) What Is a "Tool Contract" and Why Does It Matter?

A tool contract is simply an agreement about how your API behaves — what it expects as input, and what it promises to return.

This matters a lot in AI systems because the LLM (or your IDE extension) will be calling this endpoint programmatically. If the response shape is unpredictable or inconsistent, the tool breaks.

### Request Shape

```json
{
  "query": "review this docker-compose for security issues",
  "tags": ["docker", "cis"],
  "top_k": 6
}
```

- `query` — the natural language question or topic you're searching for
- `tags` — optional filters to narrow results to specific frameworks
- `top_k` — how many chunks to return

### Response Shape

```json
{
  "query": "...",
  "class": "ExpandedVSCodeMemory",
  "top_k": 6,
  "results": [
    {
      "score": 0.83,
      "title": "CIS Docker Benchmark",
      "source": "docker-security",
      "tags": ["docker", "cis"],
      "chunk_index": 12,
      "doc_path": "security-memory/data/docker-security/cis-docker-benchmark.md",
      "text": ".... chunk text ...."
    }
  ]
}
```

> **Weaviate note:** The response uses `"class"` instead of `"collection"` — matching Weaviate's terminology. Under the hood, the API uses a GraphQL `nearVector` query to Weaviate rather than Qdrant's REST search endpoint. The response shape exposed to callers is identical.

- `results[*].text` is the actual content you paste into a prompt
- `tags` and `doc_path` tell you where the answer came from — making results auditable
- `score` is the similarity score — closer to 1.0 means a stronger match

---

## 2) What Files Are Being Added and What Does Each One Do?

This lesson introduces a new Python package inside the `ingestion-api` container:

```
ingestion-api/app/security_memory/
  router.py
  schemas.py
  store.py
  ingest.py
  __init__.py
```

- **`router.py`** — defines the FastAPI endpoints (`/memory/health` and `/memory/query`). The "front door" of the tool.
- **`schemas.py`** — defines the Pydantic models that describe valid requests and responses. Pydantic validates incoming data automatically.
- **`store.py`** — the core logic. Takes a query string, embeds it via Ollama, then sends that embedding to Weaviate as a `nearVector` GraphQL query to find the closest matching chunks. Also powers `/memory/health` by checking the Weaviate class status.
- **`ingest.py`** — the ingestion script you ran in Lesson 4.1. Lives here so you can re-run it inside the container if you add new documents.
- **`__init__.py`** — tells Python this folder is a package.

All of these files already exist in the repo — you don't need to create or copy anything.

---

## 3) Rebuild and Test Your Endpoints

First, rebuild the ingestion API container to pick up the new module:

```bash
docker compose up -d --build ingestion-api
```

All requests go through NGINX, which enforces your API key. Pull your key from `.env`:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

### Test 1: Health Check

```bash
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/memory/health | python -m json.tool
```

You should see something like:

```json
{
  "ok": true,
  "class": "ExpandedVSCodeMemory",
  "object_count": 142
}
```

If `ok` is `false` or `object_count` is `0`, ingestion hasn't run yet or the class name doesn't match. Go back to Lesson 4.1 and re-run ingestion.

### Test 2: Query

```bash
curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"what is broken access control", "tags":["owasp"], "top_k": 5}' \
  | python -m json.tool
```

You should get back a list of results with real text from your OWASP documents. If results are empty, check that your OWASP docs were ingested and that the tag `owasp` was assigned correctly during ingestion.

---

## 4) Optional: Connect Memory to Your `/chat` Endpoint

Once `/memory/query` is working, you can connect it to your existing `/chat` endpoint so that security questions are automatically answered using your curated standards rather than just the model's training data.

The idea: before the prompt is built, check whether the question is security-related. If it is, fetch relevant chunks from memory and inject them into the prompt as additional context. If not, the chat works exactly as before.

### Step 1 — Add the security classifier function

Open `ingestion-api/app/main.py`. Scroll to the line that reads `# Core chat implementation` and place this function directly above it:

```python
async def is_security_related(message: str) -> bool:
    """
    Asks Ollama to classify whether the message is security-related.
    Returns True if yes, False if no.
    """
    prompt = (
        "Your only job is to decide if the following message is related to "
        "cybersecurity, infrastructure security, secure coding, or security frameworks "
        "(OWASP, CIS, NIST, MITRE, etc.).\n"
        "Reply with only the word YES or NO. No explanation.\n\n"
        f"Message: {message}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            r.raise_for_status()
            answer = (r.json().get("response") or "").strip().upper()
            return answer.startswith("YES")
    except Exception:
        return False
```

### Step 2 — Add the memory fetch function

Directly below `is_security_related`, add:

```python
async def get_memory_context(query: str, top_k: int = 4) -> str:
    """
    Calls /memory/query and returns the retrieved chunks as a formatted string
    ready to inject into a prompt.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "http://localhost:8000/memory/query",
                json={"query": query, "top_k": top_k}
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("results"):
                return ""
            chunks = []
            for result in data["results"]:
                chunks.append(f"[{result['title']} | {result['source']}]\n{result['text']}")
            return "\n\n".join(chunks)
    except Exception:
        return ""
```

> **Note:** `http://localhost:8000/memory/query` works here because both functions live inside the same `ingestion-api` container. This is an internal call that never goes through NGINX, so no API key is needed.

### Step 3 — Update `_chat_impl` to use both functions

Find the `_chat_impl` function and add the security check right at the top:

```python
async def _chat_impl(
    message: str,
    rid: str,
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = None,
):
    t0 = time.time()

    # 0) Security memory injection (optional enhancement)
    if await is_security_related(message):
        memory_context = await get_memory_context(message)
    else:
        memory_context = ""

    # 1) Retrieve
    t_retr0 = time.time()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
```

Then find the `build_prompt` call and replace it with:

```python
enriched_message = (
    f"Security reference material:\n{memory_context}\n\nQuestion: {message}"
    if memory_context
    else message
)
prompt = await asyncio.wait_for(
    asyncio.to_thread(build_prompt, enriched_message, sources, detail_level),
    timeout=PROMPT_TIMEOUT_S,
)
```

The rest of `_chat_impl` — the Ollama call, the timing, and the response shape — stays completely unchanged.

---

---

**5) — Add follow-up question suggestions (optional)**

This step adds a second Ollama call after the answer is generated. It looks at the question and answer and suggests 2-3 relevant follow-up questions the user might want to ask next. These are returned alongside the answer and displayed as clickable buttons in the Gradio UI.

Add this function directly below `get_memory_context`:

```python
async def get_followup_suggestions(message: str, answer: str) -> list:
    """
    Asks Ollama to suggest 2-3 follow-up questions based on the question and answer.
    Returns a list of question strings, or an empty list if it fails.
    """
    prompt = (
        "Based on this question and answer, suggest 2-3 short follow-up questions "
        "the user might want to ask next. Return only the questions as a JSON array "
        "of strings with no extra text, no explanation, and no markdown.\n\n"
        f"Question: {message}\n\nAnswer: {answer}"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            r.raise_for_status()
            response = (r.json().get("response") or "").strip()
            return json.loads(response)
    except Exception:
        return []
```

Make sure `import json` is at the top of `main.py` with the other imports.

Then update `_chat_impl` to call it after the answer is generated. Find the return block at the bottom of `_chat_impl`:

```python
    return {
        "answer": answer,
        "sources": sources,
        ...
    }
```

Replace it with:

```python
    # 4) Follow-up suggestions
    followups = await get_followup_suggestions(message, answer)

    return {
        "answer": answer,
        "sources": sources,
        "followups": followups,
        "_timing_ms": {
            "retrieve": round(t_retr, 1),
            "prompt": round(t_pr, 1),
            "generate": round(t_llm, 1),
            "total": round(total, 1),
        },
        "_prompt_chars": len(prompt),
    }
```

Also update the `/chat` endpoint to pass `followups` through to the response. Find:

```python
        return {"answer": result["answer"], "sources": result["sources"]}
```

Replace with:

```python
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "followups": result.get("followups", []),
        }
```

Once this is in place, the `/chat` response will include a `followups` field — a list of suggested questions. The Gradio UI update in Lesson 4.3 will display these as clickable buttons.

## 6) Security Note: Keep These Endpoints Behind the API Key Gate

The memory endpoints contain curated security reference material. Make sure they follow the same auth rules as the rest of the API:

- Do **not** expose `ingestion-api` directly on a host port — traffic should always go through `edge-nginx`
- Do **not** disable the `X-API-Key` check during testing (use the `$EDGE_API_KEY` variable instead)
- If you're unsure whether your endpoints are protected, re-read the NGINX config to confirm all `/memory/*` paths require the key

---
# Now rebuilt ingestion_api
```bash
docker compose up -d --build ingestion-api
docker cp patches/ingestion-api/app/security_memory ingestion-api:/app/app/security_memory
docker compose restart ingestion-api
```
Run this to test the chat endpoint in terminal:
```bash
curl -s -X POST http://localhost:8088/chat -H "Content-Type: application/json" -H "X-API-Key: $EDGE_API_KEY" -d '{"message": "What are the CIS Docker benchmark recommendations for running containers as root?"}' | python -m json.tool
```
If chat times out add this to the .env file:
```bash
CHAT_TOTAL_TIMEOUT_S=300
OLLAMA_TIMEOUT_S=240
```

## Checkpoint

You're done when all of the following are true:

- [ ] `/memory/health` returns `ok: true` through `http://localhost:8088`
- [ ] `/memory/query` returns relevant, non-empty results
- [ ] The base lab still works (chat, ingest, and retrieval are unaffected)

---

[← Lesson 1](01-building-security-memory.md) | [Lesson 3 →](03-ide-integration.md)
