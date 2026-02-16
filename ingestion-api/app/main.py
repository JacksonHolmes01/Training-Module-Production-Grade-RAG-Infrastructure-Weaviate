import os
import time
import traceback
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse

from .schemas import ArticleIn, ChatIn
from .weaviate_client import ready, ensure_schema, insert_doc
from .rag import retrieve_sources, build_prompt, ollama_generate

EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")

app = FastAPI(title="Lab 2 Ingestion + RAG API")

START = time.time()
INGEST_COUNT = 0
CHAT_COUNT = 0
ERROR_COUNT = 0


def require_api_key(request: Request):
    """Simple API-key auth used for teaching boundaries."""
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="EDGE_API_KEY is not set on the server.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if incoming != EDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")


@app.get("/health")
async def health():
    """Returns API health plus a Weaviate readiness check."""
    w_ok = await ready()
    return {
        "ok": bool(w_ok),
        "uptime_s": int(time.time() - START),
        "ingested": INGEST_COUNT,
        "chats": CHAT_COUNT,
        "errors": ERROR_COUNT,
        "ollama_model": os.getenv("OLLAMA_MODEL", ""),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Tiny counters (teaching aid)."""
    return (
        f"ingestion_api_ingested_total {INGEST_COUNT}\n"
        f"ingestion_api_chats_total {CHAT_COUNT}\n"
        f"ingestion_api_errors_total {ERROR_COUNT}\n"
    )


@app.post("/ingest")
async def ingest(article: ArticleIn, request: Request):
    """Validate and ingest a document into Weaviate."""
    global INGEST_COUNT, ERROR_COUNT
    require_api_key(request)

    try:
        await ensure_schema()
        # insert_doc already JSON-safes in your updated weaviate_client
        res = await insert_doc(article.model_dump())
        INGEST_COUNT += 1
        return {"status": "ok", "weaviate": res}
    except Exception as e:
        ERROR_COUNT += 1
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(payload: ChatIn, request: Request):
    """RAG endpoint: retrieve top-K sources from Weaviate, then generate with Ollama."""
    global CHAT_COUNT, ERROR_COUNT
    require_api_key(request)

    try:
        sources = await retrieve_sources(payload.message)
        prompt = build_prompt(payload.message, sources)
        answer = await ollama_generate(prompt)
        CHAT_COUNT += 1
        return {"answer": answer, "sources": sources}
    except Exception as e:
        ERROR_COUNT += 1
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Debug endpoints (teaching aid)
# -----------------------------
@app.get("/debug/retrieve")
async def debug_retrieve(request: Request, q: str = Query(min_length=2, max_length=2000)):
    """Return retrieval results WITHOUT calling the LLM."""
    require_api_key(request)
    try:
        sources = await retrieve_sources(q)
        return {"query": q, "sources": sources}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/prompt")
async def debug_prompt(payload: ChatIn, request: Request):
    """Return the exact prompt that would be sent to the LLM (plus sources)."""
    require_api_key(request)
    try:
        sources = await retrieve_sources(payload.message)
        prompt = build_prompt(payload.message, sources)
        return {"prompt": prompt, "sources": sources}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/ollama")
async def debug_ollama(payload: ChatIn, request: Request) -> Dict[str, Any]:
    """
    Call Ollama directly with a VERY small prompt.
    This isolates whether generation works, independent of Weaviate and prompt size.
    """
    require_api_key(request)
    try:
        # Keep prompt small to avoid token/context issues while debugging
        small_prompt = f"Answer in 2 sentences:\n{payload.message}"
        answer = await ollama_generate(small_prompt)
        return {
            "ok": True,
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
            "ollama_model": os.getenv("OLLAMA_MODEL", ""),
            "answer": answer,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
