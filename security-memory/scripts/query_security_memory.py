"""
Query ExpandedVSCodeMemory via Weaviate REST (nearVector).

Usage:
    python security-memory/scripts/query_security_memory.py "owasp broken access control"

Requires:
- Weaviate URL (default: http://localhost:8080)
- Ollama URL (default: http://localhost:11434) for embeddings
"""
import os, sys, json, asyncio
import httpx

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
SECURITY_CLASS = os.getenv("SECURITY_CLASS", "ExpandedVSCodeMemory")
SECURITY_EMBED_MODEL = os.getenv("SECURITY_EMBED_MODEL", "nomic-embed-text")
TOP_K = int(os.getenv("SECURITY_TOP_K", "6"))


async def embed(q: str) -> list:
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": SECURITY_EMBED_MODEL, "prompt": q}
        )
        r.raise_for_status()
        return r.json()["embedding"]


async def main():
    if len(sys.argv) < 2:
        raise SystemExit("Provide a query string.")
    q = " ".join(sys.argv[1:])
    vec = await embed(q)

    # Weaviate GraphQL nearVector query
    graphql = {
        "query": f"""
        {{
          Get {{
            {SECURITY_CLASS}(
              nearVector: {{ vector: {json.dumps(vec)} }}
              limit: {TOP_K}
            ) {{
              text
              title
              source
              tags
              chunk_index
              doc_path
              _additional {{ distance }}
            }}
          }}
        }}
        """
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.post(f"{WEAVIATE_URL}/v1/graphql", json=graphql)
        r.raise_for_status()
        data = r.json()

    hits = data.get("data", {}).get("Get", {}).get(SECURITY_CLASS, [])
    out = []
    for h in hits:
        out.append({
            "score": 1 - (h.get("_additional", {}).get("distance") or 0),
            "title": h.get("title"),
            "source": h.get("source"),
            "tags": h.get("tags"),
            "chunk_index": h.get("chunk_index"),
            "doc_path": h.get("doc_path"),
            "text_preview": (h.get("text") or "")[:260],
        })

    print(json.dumps({"query": q, "class": SECURITY_CLASS, "results": out}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
