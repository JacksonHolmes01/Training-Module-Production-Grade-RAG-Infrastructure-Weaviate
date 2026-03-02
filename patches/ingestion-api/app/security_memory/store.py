import json
import os
from typing import List, Dict, Any, Optional

import httpx

from .schemas import MemoryQueryIn, MemoryQueryOut, MemoryChunk, MemoryHealthOut

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")

SECURITY_CLASS = os.getenv("SECURITY_CLASS", "ExpandedVSCodeMemory")
SECURITY_TOP_K = int(os.getenv("SECURITY_TOP_K", "6"))
SECURITY_EMBED_MODEL = os.getenv("SECURITY_EMBED_MODEL", "nomic-embed-text")
SECURITY_EMBED_DIM = int(os.getenv("SECURITY_EMBED_DIM", "768"))


async def _embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using Ollama. Returns one vector per text."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        vectors = []
        for text in texts:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": SECURITY_EMBED_MODEL, "prompt": text},
            )
            r.raise_for_status()
            vectors.append(r.json()["embedding"])
        return vectors


async def _ensure_class() -> None:
    """Create the Weaviate class schema if it does not already exist."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{WEAVIATE_URL}/v1/schema/{SECURITY_CLASS}")
        if r.status_code == 200:
            return
        schema = {
            "class": SECURITY_CLASS,
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
            "properties": [
                {"name": "text",        "dataType": ["text"]},
                {"name": "title",       "dataType": ["text"]},
                {"name": "source",      "dataType": ["text"]},
                {"name": "doc_path",    "dataType": ["text"]},
                {"name": "tags",        "dataType": ["text[]"]},
                {"name": "chunk_index", "dataType": ["int"]},
            ],
        }
        cr = await client.post(f"{WEAVIATE_URL}/v1/schema", json=schema)
        cr.raise_for_status()


async def memory_health() -> MemoryHealthOut:
    await _ensure_class()
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Weaviate readiness check
        hz = await client.get(f"{WEAVIATE_URL}/v1/.well-known/ready")
        ok = hz.status_code == 200

        # Count objects in class via GraphQL aggregate
        gql = {"query": f"{{ Aggregate {{ {SECURITY_CLASS} {{ meta {{ count }} }} }} }}"}
        count_resp = await client.post(f"{WEAVIATE_URL}/v1/graphql", json=gql)
        object_count: Optional[int] = None
        if count_resp.status_code == 200:
            try:
                object_count = (
                    count_resp.json()
                    .get("data", {})
                    .get("Aggregate", {})
                    .get(SECURITY_CLASS, [{}])[0]
                    .get("meta", {})
                    .get("count")
                )
            except Exception:
                object_count = None

    note = None
    if object_count in (0, None):
        note = (
            "Class exists but appears empty. "
            "Run: docker exec -i ingestion-api python -m app.security_memory.ingest"
        )

    return MemoryHealthOut.model_validate(
        {
            "ok": ok,
            "class": SECURITY_CLASS,
            "weaviate_url": WEAVIATE_URL,
            "object_count": object_count,
            "note": note,
        }
    )


async def query_memory(payload: MemoryQueryIn) -> MemoryQueryOut:
    await _ensure_class()
    top_k = payload.top_k or SECURITY_TOP_K

    # Embed the query via Ollama
    qvec = (await _embed([payload.query]))[0]

    # Build Weaviate GraphQL nearVector query
    # Tags filter: match objects where tags array contains ANY of the requested tags
    where_clause = ""
    if payload.tags:
        # Weaviate OR filter: one operand per tag using containsAny on text[]
        tag_filters = ", ".join(
            f'{{ path: ["tags"], operator: Equal, valueText: "{t}" }}'
            for t in payload.tags
        )
        where_clause = f"where: {{ operator: Or, operands: [{tag_filters}] }}"

    graphql_query = f"""
    {{
      Get {{
        {SECURITY_CLASS}(
          nearVector: {{ vector: {json.dumps(qvec)} }}
          limit: {top_k}
          {where_clause}
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

    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.post(
            f"{WEAVIATE_URL}/v1/graphql",
            json={"query": graphql_query},
        )
        r.raise_for_status()
        data = r.json()

    hits: List[Dict[str, Any]] = (
        data.get("data", {}).get("Get", {}).get(SECURITY_CLASS) or []
    )

    results: List[MemoryChunk] = []
    for h in hits:
        # Weaviate returns distance (0=identical, 2=opposite for cosine).
        # Convert to a similarity score in [0, 1].
        distance = (h.get("_additional") or {}).get("distance") or 0.0
        score = max(0.0, 1.0 - float(distance))
        results.append(
            MemoryChunk(
                score=score,
                title=str(h.get("title") or ""),
                source=str(h.get("source") or ""),
                tags=list(h.get("tags") or []),
                text=str(h.get("text") or ""),
                chunk_index=int(h.get("chunk_index") or 0),
                doc_path=str(h.get("doc_path") or ""),
            )
        )

    return MemoryQueryOut.model_validate(
        {
            "query": payload.query,
            "class": SECURITY_CLASS,
            "top_k": top_k,
            "results": results,
        }
    )
