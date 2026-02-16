import os
import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

async def ollama_generate(prompt: str) -> str:
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 80,        # HARD CAP tokens (~2-3 sentences)
            "temperature": 0.2,       # lower = less rambling
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MAX_SOURCE_CHARS = int(os.getenv("RAG_MAX_SOURCE_CHARS", "1200"))

async def retrieve_sources(query: str, k: int | None = None):
    """Retrieve top-k documents from Weaviate using nearText."""
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


