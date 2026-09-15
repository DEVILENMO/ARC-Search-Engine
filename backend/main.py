# -*- coding: utf-8 -*-
"""ARC Search Engine — unified Python backend (FastAPI).

One process replaces the original two-service topology (Java Spring Boot +
Python Tornado): REST API, WebSocket push, indexing pipeline and the LLM
features all live here, so a single `python main.py` starts the engine.

Routes kept byte-compatible with the Java backend so the Vue frontend works
unchanged (port 8899):
  POST /search/get      {"keywords": "..."}          -> {results, keywordsTokenId, relatedResList}
  POST /AIChat/getReply {"sessionId", "userQuery"}   -> plain-text reply
  POST /PageLink/Parse  {"urls": "url1 10, url2 20"} -> number of accepted tasks
  WS   /websocket       push {type, msg}: 0=related words, 1=AI summary, 2=crawl progress
"""
import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ai import LLMUnavailableError, assistant_reply
from config import (CRAWLER_MAX_DEPTH, CRAWLER_MAX_WORKERS, CHAT_MEMORY_TTL_SECONDS,
                    SERVICE_HOST, SERVICE_PORT)
from indexer import Indexer
from search_engine import SearchEngine
from storage import Database, make_cache
from tokenizer import SearchEngineTokenizer

# `config` module itself is referenced in the lifespan error hint below
import config  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# shared state (initialized in lifespan)
# ---------------------------------------------------------------------------
loop: asyncio.AbstractEventLoop | None = None
db: Database | None = None
engine: SearchEngine | None = None
indexer: Indexer | None = None
executor: ThreadPoolExecutor | None = None


class ConnectionManager:
    """All connected browsers; the original design broadcasts globally."""

    def __init__(self):
        self._active: set[WebSocket] = set()
        self._lock = threading.Lock()

    def connect(self, websocket: WebSocket):
        with self._lock:
            self._active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        with self._lock:
            self._active.discard(websocket)

    async def broadcast(self, msg_type: int, msg: dict):
        payload = {'type': msg_type, 'msg': msg}
        with self._lock:
            targets = list(self._active)
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)


manager = ConnectionManager()


def broadcast_threadsafe(msg_type: int, msg: dict):
    """Push a WebSocket message from a worker thread onto the event loop."""
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast(msg_type, msg), loop)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    global loop, db, engine, indexer, executor
    loop = asyncio.get_running_loop()

    cache = make_cache()
    db = Database(cache)
    try:
        db.ensure_collections()
    except Exception as e:
        raise RuntimeError(
            f'Cannot reach MongoDB ({config.MONGO_URI}). Start it with `docker compose up -d` '
            f'or set MONGO_URI. Root cause: {e}') from e

    logger.info('Loading GPT-2 tokenizer...')
    tokenizer = SearchEngineTokenizer()

    executor = ThreadPoolExecutor(max_workers=CRAWLER_MAX_WORKERS + 2, thread_name_prefix='arc')
    indexer = Indexer(db, tokenizer)
    engine = SearchEngine(db, tokenizer, submit_task=executor.submit, broadcast=broadcast_threadsafe)

    logger.info('ARC search engine ready: http://%s:%d (corpus: %d pages)',
                SERVICE_HOST, SERVICE_PORT, db.count_pages())
    yield
    executor.shutdown(wait=False)


app = FastAPI(title='ARC Search Engine', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ---------------------------------------------------------------------------
# request/response models
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    keywords: str


class ChatRequest(BaseModel):
    sessionId: str
    userQuery: str


class CrawlRequest(BaseModel):
    # "https://a.com 10, https://b.com 100"
    urls: str


# ---------------------------------------------------------------------------
# REST routes (paths kept from the Java backend)
# ---------------------------------------------------------------------------
@app.get('/health')
def health():
    return {'status': 'ok', 'pages': db.count_pages()}


@app.post('/search/get')
def search_get(request: SearchRequest):
    return engine.search(request.keywords)


@app.post('/AIChat/getReply', response_class=PlainTextResponse)
def ai_chat(request: ChatRequest):
    cache = db.cache
    memory_key = f'chat_{request.sessionId}'
    history = cache.get(memory_key) or []
    history.append({'role': 'user', 'content': request.userQuery})
    try:
        reply = assistant_reply(history)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=502, detail=f'LLM backends unavailable: {e}') from e
    history.append({'role': 'assistant', 'content': reply})
    cache.set(memory_key, history, ttl_seconds=CHAT_MEMORY_TTL_SECONDS)
    return reply


@app.post('/PageLink/Parse')
def parse_page_links(request: CrawlRequest):
    accepted = 0
    for part in request.urls.split(','):
        bits = part.strip().split(' ')
        if not bits or not bits[0]:
            continue
        start_url = bits[0]
        max_suburl = 50
        if len(bits) > 1 and bits[1].isdigit():
            max_suburl = int(bits[1])
        executor.submit(_crawl_job, start_url, max_suburl, CRAWLER_MAX_DEPTH)
        accepted += 1
    return accepted


def _crawl_job(start_url: str, max_suburl: int, max_depth: int):
    indexer.crawl_and_index(
        start_url, max_suburl, max_depth,
        on_progress=lambda done, total: broadcast_threadsafe(
            2, {'taskNum': total, 'finishNum': done, 'startUrl': start_url}),
    )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket('/websocket')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.connect(websocket)
    logger.info('WebSocket client connected (%d total)', len(manager._active))
    try:
        while True:
            await websocket.receive_text()  # keepalive; clients send nothing meaningful
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info('WebSocket client disconnected')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
