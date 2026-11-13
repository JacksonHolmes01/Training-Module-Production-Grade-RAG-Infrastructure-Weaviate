"""
db.py: Weaviate access layer.

Security design:
  - Weaviate requires an API key for every request, and role-based access
    control (RBAC) decides what each key may do.
  - The ADMIN key never reaches this API. It is used once, by the
    weaviate-init container, to create the collection, the tenant, and
    the roles.
  - This API holds two keys, each tied to a user with one role:
      * rag-writer: may only CREATE objects in this tenant. It cannot read,
        change, or delete anything. Used ONLY by /ingest.
      * rag-reader: may only READ objects in this tenant. Used by /chat
        and retrieval.
    If the chat path is ever abused, its key cannot change data, and
    neither key can touch another tenant's data or change the schema.
  - Keys are read from Docker secret files, never from env vars.
  - Part 4: traffic to Weaviate can be encrypted and verified (WEAVIATE_CA_CERT).
  - Weaviate's built-in multi-tenancy keeps each tenant's data in its own
    shard. The tenant comes from server configuration (APP_TENANT),
    never from the HTTP request.
"""

import json
import os
import logging
import uuid
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("db")

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
APP_TENANT   = os.getenv("APP_TENANT", "lab")
EMBED_DIM    = int(os.getenv("EMBED_DIM", "768"))
COLLECTION   = "LabDocs"
# Part 4 (Layer 5): with WEAVIATE_URL=https://... the connection is encrypted,
# and WEAVIATE_CA_CERT makes the API check Weaviate's certificate against our
# own certificate authority, so an impostor cannot pose as the database.
WEAVIATE_CA_CERT = os.getenv("WEAVIATE_CA_CERT", "")
FIELDS       = "title url source published_date tags content"


def _secret(name: str) -> str:
    with open(f"/run/secrets/{name}", "r", encoding="utf-8") as f:
        return f.read().strip()


def _client(key_name: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=WEAVIATE_URL,
        headers={"Authorization": f"Bearer {_secret(key_name)}"},
        timeout=30.0,
        verify=WEAVIATE_CA_CERT or True,
    )


writer: httpx.AsyncClient | None = None
reader: httpx.AsyncClient | None = None


async def open_pools() -> None:
    global writer, reader
    writer = _client("weaviate_writer_key")
    reader = _client("weaviate_reader_key")


async def close_pools() -> None:
    for c in (writer, reader):
        if c is not None:
            await c.aclose()


def _check_dim(vec: List[float]) -> List[float]:
    if len(vec) != EMBED_DIM:
        raise ValueError(f"Embedding has {len(vec)} dimensions, expected {EMBED_DIM}.")
    return [float(x) for x in vec]


async def _graphql(query: str) -> Dict[str, Any]:
    r = await reader.post("/v1/graphql", json={"query": query})
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(f"Weaviate query failed: {body['errors'][0].get('message', '')[:200]}")
    return body.get("data") or {}


async def ready() -> bool:
    try:
        r = await reader.get(f"/v1/schema/{COLLECTION}")
        return r.status_code == 200
    except Exception as e:
        logger.warning("Weaviate not ready: %s", e)
        return False


async def insert_doc(doc: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
    obj_id = str(uuid.uuid4())
    properties = {
        "title": doc.get("title", ""),
        "url": doc.get("url", ""),
        "source": doc.get("source", ""),
        "published_date": doc.get("published_date", ""),
        "tags": doc.get("tags", []),
        "content": doc["text"],
    }
    r = await writer.post("/v1/objects", json={
        "class": COLLECTION, "tenant": APP_TENANT, "id": obj_id,
        "properties": properties, "vector": _check_dim(embedding),
    })
    r.raise_for_status()
    return {"id": obj_id, "tenant": APP_TENANT}


async def search(embedding: List[float], k: int) -> List[Dict[str, Any]]:
    vec = json.dumps(_check_dim(embedding))
    data = await _graphql(
        f'{{Get{{{COLLECTION}(tenant: {json.dumps(APP_TENANT)}, nearVector: {{vector: {vec}}}, limit: {int(k)})'
        f'{{{FIELDS} _additional{{id distance}}}}}}}}'
    )
    out = []
    for o in (data.get("Get") or {}).get(COLLECTION) or []:
        extra = o.pop("_additional", {}) or {}
        out.append({"id": extra.get("id"), **o, "distance": float(extra.get("distance") or 0.0)})
    return out


async def count_docs() -> int:
    data = await _graphql(f'{{Aggregate{{{COLLECTION}(tenant: {json.dumps(APP_TENANT)}){{meta{{count}}}}}}}}')
    rows = (data.get("Aggregate") or {}).get(COLLECTION) or [{}]
    return int((rows[0].get("meta") or {}).get("count", 0))


async def all_docs(limit: int = 5000) -> List[Dict[str, Any]]:
    """Every stored document for this tenant (read-only key). Used by /debug/scan."""
    data = await _graphql(
        f'{{Get{{{COLLECTION}(tenant: {json.dumps(APP_TENANT)}, limit: {int(limit)}){{title content _additional{{id}}}}}}}}'
    )
    return [{"id": (o.get("_additional") or {}).get("id"), "title": o.get("title", ""),
             "content": o.get("content", "")} for o in (data.get("Get") or {}).get(COLLECTION) or []]
