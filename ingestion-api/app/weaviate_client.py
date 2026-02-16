import os
import httpx

WEAVIATE_SCHEME = os.getenv("WEAVIATE_SCHEME", "http")
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "weaviate")
WEAVIATE_PORT = os.getenv("WEAVIATE_PORT", "8080")
WEAVIATE_BASE = f"{WEAVIATE_SCHEME}://{WEAVIATE_HOST}:{WEAVIATE_PORT}"

WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")

def _headers():
    if WEAVIATE_API_KEY:
        return {"Authorization": f"Bearer {WEAVIATE_API_KEY}"}
    return {}

async def ready() -> bool:
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{WEAVIATE_BASE}/v1/.well-known/ready", headers=_headers())
        return r.status_code == 200

async def ensure_schema():
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

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{WEAVIATE_BASE}/v1/schema", headers=_headers())
        r.raise_for_status()
        classes = [c.get("class") for c in r.json().get("classes", [])]
        if "LabDoc" in classes:
            return

        cr = await client.post(f"{WEAVIATE_BASE}/v1/schema", json=schema, headers=_headers())
        cr.raise_for_status()

async def insert_doc(doc: dict):
    # Ensure Pydantic Url / datetime / etc become JSON-safe primitives
    if hasattr(doc, "model_dump"):
        doc = doc.model_dump(mode="json")

    # If a dict still contains Url objects, coerce anything non-primitive to str
    safe_doc = {}
    for k, v in (doc or {}).items():
        if v is None or isinstance(v, (str, int, float, bool, list, dict)):
            safe_doc[k] = v
        else:
            safe_doc[k] = str(v)

    payload = {"class": "LabDoc", "properties": safe_doc}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{WEAVIATE_BASE}/v1/objects", json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()
