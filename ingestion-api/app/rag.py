import os
import httpx
from typing import Optional, List, Dict, Any

# -----------------------------
# Weaviate config
# -----------------------------
WEAVIATE_SCHEME = os.getenv("WEAVIATE_SCHEME", "http")
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "weaviate")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_BASE = f"{WEAVIATE_SCHEME}://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

def _headers() -> dict:
    """
    If Weaviate auth is enabled in your deployment, set WEAVIATE_API_KEY.
    In your lab config it may be blank (which is fine).
    """
    if WEAVIATE_API_KEY:
        return {"Authorization": f"Bearer {WEAVIATE_API_KEY}"}
    return {}

async def ensure_schema() -> None:
    """
    Ensure the LabDoc class exists.
    Safe to call repeatedly.
    """
    schema = {
        "class": "LabDoc",
        "vectorizer": "text2vec-transformers",
        "properties": [
            {"name": "title", "dataType": ["text"]},
            {"name": "url", "dataType": ["text"]},
            {"name": "source", "dataType": ["text"]},
            {"name": "published_date", "dataType": ["text"]},
            {"name": "text", "dataType": ["text"]},
        ],
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{WEAVIATE_BASE}/v1/schema", headers=_headers())
        r.raise_for_status()
        classes = [c.get("class") for c in (r.json().get("classes", []) or [])]
        if "LabDoc" in classes:
            return

        # Weaviate accepts POST /v1/schema with {"class": "..."}
        cr = await client.post(f"{WEAVIATE_BASE}/v1/schema", json=schema, headers=_headers())
        cr.raise_for_status()

# -----------------------------
# Ollama config
# -----------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

async def ollama_generate(prompt: str) -> str:
    """
    Generate an answer using Ollama.
    Uses non-streaming mode and caps tokens to keep answers short.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            # Hard cap output length; tune as needed
            "num_predict": 120,
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()

# -----------------------------
# RAG tuning
# -----------------------------
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MAX_SOURCE_CHARS = int(os.getenv("RAG_MAX_SOURCE_CHARS", "1200"))

async def retrieve_sources(query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve top-k documents from Weaviate using nearText on LabDoc.
    """
    await ensure_schema()

    k = k or RAG_TOP_K
    safe_query = query.replace('"', '\\"')

    gql = {
        "query": (
            "{\n"
            "  Get {\n"
            f'    LabDoc(limit: {k}, nearText: {{ concepts: ["{safe_query}"] }}) {{\n'
            "      title\n"
            "      url\n"
            "      source\n"
            "      published_date\n"
            "      text\n"
            "      _additional { distance }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.post(f"{WEAVIATE_BASE}/v1/graphql", json=gql, headers=_headers())
        r.raise_for_status()
        docs = (r.json().get("data", {}) or {}).get("Get", {}).get("LabDoc", []) or []

    sources: List[Dict[str, Any]] = []
    for d in docs:
        full_text = d.get("text") or ""
        sources.append(
            {
                "title": d.get("title") or "",
                "url": d.get("url") or "",
                "source": d.get("source") or "",
                "published_date": d.get("published_date") or "",
                "distance": (d.get("_additional", {}) or {}).get("distance"),
                "snippet": full_text[:RAG_MAX_SOURCE_CHARS],
            }
        )

    return sources

def build_prompt(user_question: str, sources: List[Dict[str, Any]]) -> str:
    if not sources:
        context = "No sources retrieved."
    else:
        blocks = []
        for i, s in enumerate(sources, start=1):
            blocks.append(
                f"""[Source {i}]
Title: {s.get('title')}
URL: {s.get('url')}
Publisher: {s.get('source')} | Date: {s.get('published_date')}
Excerpt:
{s.get('snippet')}
"""
            )
        context = "\n\n".join(blocks)

    return f"""You are a helpful assistant answering questions using ONLY the provided sources.
If the sources are insufficient, say that clearly and suggest what information to add.

User question:
{user_question}

Sources:
{context}

Instructions:
- Write a clear answer.
- Use plain language.
- At the end, list which sources you used (example: "Used sources: 1, 3").
"""
