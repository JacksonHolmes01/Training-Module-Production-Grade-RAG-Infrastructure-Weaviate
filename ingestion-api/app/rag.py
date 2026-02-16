import os
import httpx

from .weaviate_client import ensure_schema, WEAVIATE_BASE, _headers

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MAX_SOURCE_CHARS = int(os.getenv("RAG_MAX_SOURCE_CHARS", "1200"))

async def retrieve_sources(query: str, k: int | None = None):
    """Retrieve top-k documents from Weaviate using nearText."""
    await ensure_schema()
    k = k or RAG_TOP_K

    safe_query = query.replace('"', '\"')

    gql = {
        "query": (
            '{\n'
            '  Get {\n'
            f'    LabDoc(limit: {k}, nearText: {{ concepts: ["{safe_query}"] }}) {{\n'
            '      title\n'
            '      url\n'
            '      source\n'
            '      published_date\n'
            '      text\n'
            '      _additional { distance }\n'
            '    }\n'
            '  }\n'
            '}\n'
        )
    }

    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(f"{WEAVIATE_BASE}/v1/graphql", json=gql, headers=_headers())
        r.raise_for_status()
        docs = r.json().get("data", {}).get("Get", {}).get("LabDoc", []) or []

    sources = []
    for d in docs:
        full_text = d.get("text") or ""
        sources.append({
            "title": d.get("title"),
            "url": d.get("url"),
            "source": d.get("source"),
            "published_date": d.get("published_date"),
            "distance": d.get("_additional", {}).get("distance"),
            "snippet": full_text[:RAG_MAX_SOURCE_CHARS],
        })
    return sources

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

async def ollama_generate(prompt: str) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
