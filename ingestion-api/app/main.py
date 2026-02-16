import os
import time
import uuid
import logging
import asyncio
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from .schemas import ArticleIn, ChatIn
from .weaviate_client import ready as weaviate_ready, ensure_schema, insert_doc
from .rag import retrieve_sources, build_prompt, ollama_generate


# -----------------------------
# Logging
# -----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ingestion-api")

# -----------------------------
# Config
# -----------------------------
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")

# Hard timeouts (seconds) so /chat never hangs forever
RETRIEVE_TIMEOUT_S = float(os.getenv("RETRIEVE_TIMEOUT_S", "20"))
PROMPT_TIMEOUT_S = float(os.getenv("PROMPT_TIMEOUT_S", "5"))
OLLAMA_TIMEOUT_S = float(os.getenv("OLLAMA_TIMEOUT_S", "120"))

# If you want a single overall timeout:
CHAT_TOTAL_TIMEOUT_S = float(os.getenv("CHAT_TOTAL_TIMEOUT_S", "150"))


app = FastAPI(title="Lab 2 Ingestion + RAG API")

START = time.time()
INGEST_COUNT = 0
CHAT_COUNT = 0
ERROR_COUNT = 0


# -----------------------------
# Helpers
# -----------------------------
def require_api_key(request: Request):
    """Simple API-key auth used for teaching boundaries."""
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="EDGE_API_KEY is not set on the server.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if incoming != EDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """Log request start/end with a request id + duration."""
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    t0 = time.perf_counter()

    logger.info(f"[{rid}] -> {request.method} {request.url.path}")

    try:
        resp = await call_next(request)
    except Exception:
        dt = (time.perf_counter() - t0) * 1000
        logger.exception(f"[{rid}] !! unhandled exception after {dt:.1f}ms")
        raise

    dt = (time.perf_counter() - t0) * 1000
    logger.info(f"[{rid}] <- {request.method} {request.url.path} {resp.status_code} ({dt:.1f}ms)")
    resp.headers["X-Request-Id"] = rid
    return resp


def _now_s() -> int:
    return int(time.time() - START)


# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
async def health():
    """Returns API health plus a Weaviate readiness check."""
    w_ok = await weaviate_ready()
    return {
        "ok": bool(w_ok),
        "uptime_s": _now_s(),
        "ingested": INGEST_COUNT,
        "chats": CHAT_COUNT,
        "errors": ERROR_COUNT,
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
    rid = getattr(request.state, "request_id", "no-rid")

    try:
        logger.info(f"[{rid}] ingest: ensuring schema")
        await asyncio.wait_for(ensure_schema(), timeout=RETRIEVE_TIMEOUT_S)

        logger.info(f"[{rid}] ingest: inserting doc")
        res = await asyncio.wait_for(insert_doc(article.model_dump()), timeout=RETRIEVE_TIMEOUT_S)

        INGEST_COUNT += 1
        return {"status": "ok", "weaviate": res}
    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] ingest: TIMEOUT")
        raise HTTPException(status_code=504, detail="Ingest timed out (schema or insert).")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] ingest: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _chat_impl(message: str, rid: str) -> Dict[str, Any]:
    """Single implementation used by /chat and debug endpoints."""
    t0 = time.perf_counter()

    # 1) Retrieve
    logger.info(f"[{rid}] chat: retrieving sources (timeout={RETRIEVE_TIMEOUT_S}s)")
    t_retr0 = time.perf_counter()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
    t_retr = (time.perf_counter() - t_retr0) * 1000
    logger.info(f"[{rid}] chat: retrieved {len(sources)} sources in {t_retr:.1f}ms")

    # 2) Prompt
    logger.info(f"[{rid}] chat: building prompt (timeout={PROMPT_TIMEOUT_S}s)")
    t_pr0 = time.perf_counter()
    prompt = await asyncio.wait_for(asyncio.to_thread(build_prompt, message, sources), timeout=PROMPT_TIMEOUT_S)
    t_pr = (time.perf_counter() - t_pr0) * 1000
    logger.info(f"[{rid}] chat: prompt built in {t_pr:.1f}ms (chars={len(prompt)})")

    # 3) Generate
    logger.info(f"[{rid}] chat: calling ollama_generate (timeout={OLLAMA_TIMEOUT_S}s)")
    t_llm0 = time.perf_counter()
    answer = await asyncio.wait_for(ollama_generate(prompt), timeout=OLLAMA_TIMEOUT_S)
    t_llm = (time.perf_counter() - t_llm0) * 1000
    logger.info(f"[{rid}] chat: ollama returned in {t_llm:.1f}ms (answer_chars={len(answer or '')})")

    total = (time.perf_counter() - t0) * 1000

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


@app.post("/chat")
async def chat(payload: ChatIn, request: Request):
    """RAG endpoint: retrieve sources -> build prompt -> generate via Ollama."""
    global CHAT_COUNT, ERROR_COUNT
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))

    try:
        # Overall timeout so nothing hangs forever
        result = await asyncio.wait_for(
            _chat_impl(payload.message, rid),
            timeout=CHAT_TOTAL_TIMEOUT_S,
        )
        CHAT_COUNT += 1
        # Do not expose internal timing by default, but keep it if you want:
        # return result
        return {"answer": result["answer"], "sources": result["sources"]}
    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="Chat timed out (overall timeout).")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Debug endpoints (teaching aid)
# -----------------------------
@app.get("/debug/retrieve")
async def debug_retrieve(request: Request, q: str = Query(min_length=2, max_length=2000)):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(q), timeout=RETRIEVE_TIMEOUT_S)
        return {"query": q, "sources": sources}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] debug/retrieve: TIMEOUT")
        raise HTTPException(status_code=504, detail="Retrieve timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] debug/retrieve: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/prompt")
async def debug_prompt(payload: ChatIn, request: Request):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(payload.message), timeout=RETRIEVE_TIMEOUT_S)
        prompt = await asyncio.wait_for(asyncio.to_thread(build_prompt, payload.message, sources), timeout=PROMPT_TIMEOUT_S)
        return {"prompt": prompt, "sources": sources, "prompt_chars": len(prompt)}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] debug/prompt: TIMEOUT")
        raise HTTPException(status_code=504, detail="Prompt build timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] debug/prompt: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/chat")
async def debug_chat(payload: ChatIn, request: Request):
    """Run full RAG and include timing + prompt size to identify where it hangs."""
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        result = await asyncio.wait_for(
            _chat_impl(payload.message, rid),
            timeout=CHAT_TOTAL_TIMEOUT_S,
        )
        # Return everything for debugging
        return result
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] debug/chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="debug/chat timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] debug/chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
