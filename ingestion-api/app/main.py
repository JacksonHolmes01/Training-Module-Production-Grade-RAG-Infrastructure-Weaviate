import os
import time
import uuid
import asyncio
import logging

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse

from .schemas import ArticleIn, ChatIn
from .weaviate_client import ready, ensure_schema, insert_doc
from .rag import retrieve_sources, build_prompt, ollama_generate


# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ingestion-api")


# -----------------------------
# Config
# -----------------------------
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")

RETRIEVE_TIMEOUT_S = float(os.getenv("RETRIEVE_TIMEOUT_S", "10"))
PROMPT_TIMEOUT_S = float(os.getenv("PROMPT_TIMEOUT_S", "5"))
OLLAMA_TIMEOUT_S = float(os.getenv("OLLAMA_TIMEOUT_S", "120"))
CHAT_TOTAL_TIMEOUT_S = float(os.getenv("CHAT_TOTAL_TIMEOUT_S", "180"))


# -----------------------------
# App + counters
# -----------------------------
app = FastAPI(title="Lab 2 Ingestion + RAG API")

START = time.time()
INGEST_COUNT = 0
CHAT_COUNT = 0
ERROR_COUNT = 0


# -----------------------------
# Middleware: request id
# -----------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    return await call_next(request)


# -----------------------------
# Auth helper
# -----------------------------
def require_api_key(request: Request):
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="EDGE_API_KEY is not set on the server.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if incoming != EDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")


# -----------------------------
# Health + metrics
# -----------------------------
@app.get("/health")
async def health():
    w_ok = await ready()
    return {
        "ok": bool(w_ok),
        "uptime_s": int(time.time() - START),
        "ingested": INGEST_COUNT,
        "chats": CHAT_COUNT,
        "errors": ERROR_COUNT,
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return (
        f"ingestion_api_ingested_total {INGEST_COUNT}\n"
        f"ingestion_api_chats_total {CHAT_COUNT}\n"
        f"ingestion_api_errors_total {ERROR_COUNT}\n"
    )


# -----------------------------
# Ingest
# -----------------------------
@app.post("/ingest")
async def ingest(article: ArticleIn, request: Request):
    """Validate and ingest a document into Weaviate."""
    global INGEST_COUNT, ERROR_COUNT
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))

    try:
        # Only ingestion needs schema creation; chat does not.
        await asyncio.wait_for(ensure_schema(), timeout=15)

        # Ensure JSON-safe primitives
        doc = article.model_dump(mode="json")
        res = await asyncio.wait_for(insert_doc(doc), timeout=20)

        INGEST_COUNT += 1
        return {"status": "ok", "weaviate": res}

    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] /ingest: TIMEOUT")
        raise HTTPException(status_code=504, detail="Ingest timed out.")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] /ingest: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Core chat implementation
# -----------------------------
async def _chat_impl(message: str, rid: str):
    t0 = time.time()

    # 1) Retrieve
    t_retr0 = time.time()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
    t_retr = (time.time() - t_retr0) * 1000

    # 2) Prompt
    t_pr0 = time.time()
    prompt = await asyncio.wait_for(
        asyncio.to_thread(build_prompt, message, sources),
        timeout=PROMPT_TIMEOUT_S,
    )
    t_pr = (time.time() - t_pr0) * 1000

    # 3) Generate
    t_llm0 = time.time()
    answer = await asyncio.wait_for(ollama_generate(prompt), timeout=OLLAMA_TIMEOUT_S)
    t_llm = (time.time() - t_llm0) * 1000

    total = (time.time() - t0) * 1000

    return {
        "answer": answer,
        "sources": sources,
        "_timing_ms": {
            "retrieve": round(t_retr, 1),
            "prompt": round(t_pr, 1),
            "generate": round(t_llm, 1),
            "total": round(total, 1),
        },
        "_prompt_chars": len(prompt),
    }


# -----------------------------
# Chat
# -----------------------------
@app.post("/chat")
async def chat(payload: ChatIn, request: Request):
    """RAG endpoint: retrieve sources -> build prompt -> generate via Ollama."""
    global CHAT_COUNT, ERROR_COUNT
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))

    try:
        result = await asyncio.wait_for(_chat_impl(payload.message, rid), timeout=CHAT_TOTAL_TIMEOUT_S)
        CHAT_COUNT += 1
        # Keep /chat clean: only answer + sources
        return {"answer": result["answer"], "sources": result["sources"]}

    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] /chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="Chat timed out.")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] /chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Debug endpoints
# -----------------------------
@app.get("/debug/retrieve")
async def debug_retrieve(request: Request, q: str = Query(min_length=2, max_length=2000)):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(q), timeout=RETRIEVE_TIMEOUT_S)
        return {"query": q, "sources": sources}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/retrieve: TIMEOUT")
        raise HTTPException(status_code=504, detail="Retrieve timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/retrieve: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/prompt")
async def debug_prompt(payload: ChatIn, request: Request):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(payload.message), timeout=RETRIEVE_TIMEOUT_S)
        prompt = await asyncio.wait_for(
            asyncio.to_thread(build_prompt, payload.message, sources),
            timeout=PROMPT_TIMEOUT_S,
        )
        return {"prompt": prompt, "sources": sources, "prompt_chars": len(prompt)}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/prompt: TIMEOUT")
        raise HTTPException(status_code=504, detail="Prompt build timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/prompt: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/chat")
async def debug_chat(payload: ChatIn, request: Request):
    """Run full RAG and include timing/prompt size to identify where it hangs."""
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        result = await asyncio.wait_for(_chat_impl(payload.message, rid), timeout=CHAT_TOTAL_TIMEOUT_S)
        return result
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="debug/chat timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/ollama")
async def debug_ollama(payload: ChatIn, request: Request):
    """Bypass retrieval and just test generation."""
    require_api_key(request)
    try:
        # Keep it simple: send the message directly (no sources)
        answer = await asyncio.wait_for(ollama_generate(payload.message), timeout=OLLAMA_TIMEOUT_S)
        return {"ok": True, "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""), "ollama_model": os.getenv("OLLAMA_MODEL", ""), "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
