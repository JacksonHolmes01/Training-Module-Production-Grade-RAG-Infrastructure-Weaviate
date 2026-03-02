"""
Expanded VSCode Implementation ingestion entrypoint (runs inside ingestion-api container).

Run:
    docker exec -i ingestion-api python -m app.security_memory.ingest

It reads:
    security-memory/data/

Requirements:
- WEAVIATE_HOST / WEAVIATE_PORT / WEAVIATE_SCHEME match the docker-compose service (default: weaviate:8080)
- OLLAMA_BASE_URL points to ollama service (default: http://ollama:11434)
- SECURITY_EMBED_MODEL is pulled in Ollama (default: nomic-embed-text)
"""
import json
import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any

import httpx

WEAVIATE_SCHEME = os.getenv("WEAVIATE_SCHEME", "http")
WEAVIATE_HOST   = os.getenv("WEAVIATE_HOST", "weaviate")
WEAVIATE_PORT   = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_URL    = f"{WEAVIATE_SCHEME}://{WEAVIATE_HOST}:{WEAVIATE_PORT}"
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")


def _weaviate_headers() -> dict:
    if WEAVIATE_API_KEY:
        return {"Authorization": f"Bearer {WEAVIATE_API_KEY}"}
    return {}

SECURITY_CLASS = os.getenv("SECURITY_CLASS", "ExpandedVSCodeMemory")
SECURITY_CHUNK_CHARS = int(os.getenv("SECURITY_CHUNK_CHARS", "1200"))
SECURITY_CHUNK_OVERLAP = int(os.getenv("SECURITY_CHUNK_OVERLAP", "200"))
SECURITY_EMBED_MODEL = os.getenv("SECURITY_EMBED_MODEL", "nomic-embed-text")
SECURITY_EMBED_DIM = int(os.getenv("SECURITY_EMBED_DIM", "768"))

DATA_DIR = Path(os.getenv("SECURITY_DATA_DIR", "/securitymemory/data"))

TAG_KEYS = [
    "nist", "cis", "mitre", "owasp", "docker", "kubernetes",
    "linux", "cloud", "iam", "sdlc", "appsec", "containers",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _guess_tags(path: Path) -> List[str]:
    s = str(path.as_posix()).lower()
    tags = [k for k in TAG_KEYS if k in s]
    return sorted(set(tags))


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _chunk(text: str, chunk_chars: int, overlap: int) -> List[str]:
    text = _normalize(text)
    if not text:
        return []
    out = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_chars)
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end == n:
            break
        start = max(0, end - overlap)
    return out


async def _embed(texts: List[str]) -> List[List[float]]:
    """Embed texts one at a time via Ollama."""
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
    """Create the Weaviate class if it does not already exist."""
    hdrs = _weaviate_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{WEAVIATE_URL}/v1/schema/{SECURITY_CLASS}", headers=hdrs)
        if r.status_code == 200:
            print(f"[security-memory] class '{SECURITY_CLASS}' already exists")
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
        cr = await client.post(f"{WEAVIATE_URL}/v1/schema", json=schema, headers=hdrs)
        cr.raise_for_status()
        print(f"[security-memory] created class '{SECURITY_CLASS}'")


async def _upsert(objects: List[Dict[str, Any]]) -> None:
    """Batch upsert objects into Weaviate."""
    batch_payload = {
        "objects": [
            {
                "class": SECURITY_CLASS,
                "id": obj["id"],
                "vector": obj["vector"],
                "properties": {k: v for k, v in obj.items() if k not in ("id", "vector")},
            }
            for obj in objects
        ]
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            f"{WEAVIATE_URL}/v1/batch/objects",
            json=batch_payload,
            headers=_weaviate_headers(),
        )
        r.raise_for_status()


async def main() -> None:
    if not DATA_DIR.exists():
        raise SystemExit(f"SECURITY_DATA_DIR not found: {DATA_DIR}")

    await _ensure_class()

    files = [
        p for p in DATA_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    ]
    if not files:
        raise SystemExit(f"No .md/.txt files found under {DATA_DIR}. Add docs and retry.")

    BATCH = 16  # smaller batch than Qdrant version since Ollama embeds one at a time
    batch_objects: List[Dict[str, Any]] = []
    total_chunks = 0

    for fp in files:
        raw = _read_text(fp)
        chunks = _chunk(raw, SECURITY_CHUNK_CHARS, SECURITY_CHUNK_OVERLAP)
        if not chunks:
            continue

        title = fp.stem.replace("_", " ").replace("-", " ").strip()
        source = fp.parent.name
        tags = _guess_tags(fp)
        rel_path = str(fp.as_posix())

        for i, ch in enumerate(chunks):
            # Deterministic UUID so re-ingestion is idempotent
            obj_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{SECURITY_CLASS}:{rel_path}:{i}",
            ))
            batch_objects.append({
                "id": obj_id,
                "_text_to_embed": ch,   # temporary key used below
                "text": ch,
                "title": title,
                "source": source,
                "tags": tags,
                "chunk_index": i,
                "doc_path": rel_path,
            })
            total_chunks += 1

            if len(batch_objects) >= BATCH:
                texts = [o.pop("_text_to_embed") for o in batch_objects]
                vecs = await _embed(texts)
                for obj, vec in zip(batch_objects, vecs):
                    obj["vector"] = vec
                await _upsert(batch_objects)
                print(f"[security-memory] upserted {total_chunks} chunks so far...")
                batch_objects = []

    if batch_objects:
        texts = [o.pop("_text_to_embed") for o in batch_objects]
        vecs = await _embed(texts)
        for obj, vec in zip(batch_objects, vecs):
            obj["vector"] = vec
        await _upsert(batch_objects)

    print(
        f"[security-memory] ingest complete: "
        f"files={len(files)} chunks={total_chunks} class={SECURITY_CLASS}"
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
