"""
Host-mode ingestion helper.

Run from repo root:
    python security-memory/scripts/ingest_security_memory.py

Assumes:
- Weaviate reachable at http://localhost:8080
- Ollama reachable at OLLAMA_BASE_URL (default: http://localhost:11434)

If you do NOT expose Ollama to host, use container-mode:
    docker exec -i ingestion-api python -m app.security_memory.ingest
"""
import os, re, uuid, asyncio
from pathlib import Path
from typing import List, Dict, Any
import httpx

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

SECURITY_CLASS = os.getenv("SECURITY_CLASS", "ExpandedVSCodeMemory")
SECURITY_CHUNK_CHARS = int(os.getenv("SECURITY_CHUNK_CHARS", "1200"))
SECURITY_CHUNK_OVERLAP = int(os.getenv("SECURITY_CHUNK_OVERLAP", "200"))
SECURITY_EMBED_MODEL = os.getenv("SECURITY_EMBED_MODEL", "nomic-embed-text")
SECURITY_EMBED_DIM = int(os.getenv("SECURITY_EMBED_DIM", "768"))

DATA_DIR = Path(os.getenv("SECURITY_DATA_DIR", "security-memory/data"))

TAG_KEYS = ["nist","cis","mitre","owasp","docker","kubernetes","linux","cloud","iam","sdlc","appsec","containers"]


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _chunk(text: str) -> List[str]:
    text = _normalize(text)
    if not text:
        return []
    out = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + SECURITY_CHUNK_CHARS)
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end == n:
            break
        start = max(0, end - SECURITY_CHUNK_OVERLAP)
    return out


def _guess_tags(path: Path) -> List[str]:
    s = str(path.as_posix()).lower()
    tags = [k for k in TAG_KEYS if k in s]
    return sorted(set(tags))


async def _ensure_class():
    """Create the Weaviate class schema if it does not already exist."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{WEAVIATE_URL}/v1/schema/{SECURITY_CLASS}")
        if r.status_code == 200:
            print(f"[host-ingest] class '{SECURITY_CLASS}' already exists")
            return
        schema = {
            "class": SECURITY_CLASS,
            "vectorizer": "none",  # we supply vectors manually via Ollama
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "properties": [
                {"name": "text",        "dataType": ["text"]},
                {"name": "title",       "dataType": ["text"]},
                {"name": "source",      "dataType": ["text"]},
                {"name": "doc_path",    "dataType": ["text"]},
                {"name": "tags",        "dataType": ["text[]"]},
                {"name": "chunk_index", "dataType": ["int"]},
            ]
        }
        cr = await client.post(f"{WEAVIATE_URL}/v1/schema", json=schema)
        cr.raise_for_status()
        print(f"[host-ingest] created class '{SECURITY_CLASS}'")


async def _embed(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts using Ollama."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        vectors = []
        for text in texts:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={"model": SECURITY_EMBED_MODEL, "prompt": text}
            )
            r.raise_for_status()
            vectors.append(r.json()["embedding"])
        return vectors


async def _upsert(objects: List[Dict[str, Any]]):
    """Batch upsert objects into Weaviate using the batch API."""
    batch_payload = {
        "objects": [
            {
                "class": SECURITY_CLASS,
                "id": obj["id"],
                "vector": obj["vector"],
                "properties": obj["properties"],
            }
            for obj in objects
        ]
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{WEAVIATE_URL}/v1/batch/objects", json=batch_payload)
        r.raise_for_status()


async def main():
    files = sorted(DATA_DIR.rglob("*"))
    files = [f for f in files if f.is_file() and f.suffix in {".md", ".txt"}]
    if not files:
        print(f"[host-ingest] no .md or .txt files found under {DATA_DIR}")
        return

    await _ensure_class()

    total = 0
    texts, metas = [], []
    BATCH = 32

    for fpath in files:
        raw = fpath.read_text(encoding="utf-8", errors="replace")
        chunks = _chunk(raw)
        tags = _guess_tags(fpath)
        title = fpath.stem.replace("_", " ").replace("-", " ").title()
        rel = str(fpath.relative_to(DATA_DIR))

        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metas.append({
                "title": title,
                "source": fpath.parts[-2] if len(fpath.parts) >= 2 else "",
                "doc_path": rel,
                "tags": tags,
                "chunk_index": i,
                "text": chunk,
            })
            total += 1

            if len(texts) >= BATCH:
                vecs = await _embed(texts)
                objs = [
                    {
                        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{SECURITY_CLASS}:{m['doc_path']}:{m['chunk_index']}")),
                        "vector": v,
                        "properties": m,
                    }
                    for m, v in zip(metas, vecs)
                ]
                await _upsert(objs)
                texts, metas = [], []

    if texts:
        vecs = await _embed(texts)
        objs = [
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{SECURITY_CLASS}:{m['doc_path']}:{m['chunk_index']}")),
                "vector": v,
                "properties": m,
            }
            for m, v in zip(metas, vecs)
        ]
        await _upsert(objs)

    print(f"[host-ingest] complete: files={len(files)} chunks={total} class={SECURITY_CLASS}")


if __name__ == "__main__":
    asyncio.run(main())
