# -*- coding: utf-8 -*-
"""Persistence layer: MongoDB collections + optional Redis cache.

Collections (inherited from the original Java backend):
  forward_index  正排表: {url, title, content, title_tf, content_tf, icon, img,
                         childrenLink, parentLink, articleId, pagerank}
  title_index    标题倒排: {_id: tokenId, indexMap: {urlKey: {url, tf}}}
  content_index  正文倒排: 同上
  stem_df        词频DF表: {_id: tokenId, df}
  phrases        短语表:   {_id: phraseId, df}
  doc_stats      文档长度: {url, title_len, content_len}   (BM25 需要)

MongoDB historically forbids '.' inside field names, so URL keys inside
indexMap are escaped ('.' -> '%2E', '%' -> '%25'). The original Java
implementation replaced '.' with '$', which silently corrupted any URL that
legitimately contains a '$'.
"""
import json
import logging
import threading
import time
from typing import Any

from pymongo import MongoClient

from config import MONGO_DB, MONGO_URI, REDIS_URL

logger = logging.getLogger(__name__)

COLL_FORWARD = 'forward_index'
COLL_TITLE_INDEX = 'title_index'
COLL_CONTENT_INDEX = 'content_index'
COLL_DF = 'stem_df'
COLL_PHRASES = 'phrases'
COLL_DOC_STATS = 'doc_stats'

# corpora-level caches that must be invalidated whenever the index changes
_INDEX_CACHE_KEYS = ['file_num', 'df_map', 'phrase_ids']


def encode_url(url: str) -> str:
    # '%' must be escaped first to keep the round-trip injective
    return url.replace('%', '%25').replace('.', '%2E')


def decode_url(url_key: str) -> str:
    return url_key.replace('%2E', '.').replace('%25', '%')


# ---------------------------------------------------------------------------
# cache abstraction: Redis when configured, in-process dict otherwise
# ---------------------------------------------------------------------------

class MemoryCache:
    """Tiny TTL cache used when no Redis is available (dev mode)."""

    def __init__(self):
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            value, expires_at = item
            if expires_at is not None and expires_at < time.time():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value, ttl_seconds: int | None = None):
        with self._lock:
            expires_at = time.time() + ttl_seconds if ttl_seconds else None
            self._data[key] = (value, expires_at)

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)


class RedisCache:
    def __init__(self, url: str):
        import redis
        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str):
        raw = self._redis.get(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value, ttl_seconds: int | None = None):
        raw = json.dumps(value, ensure_ascii=False)
        if ttl_seconds:
            self._redis.setex(key, ttl_seconds, raw)
        else:
            self._redis.set(key, raw)

    def delete(self, key: str):
        self._redis.delete(key)


def make_cache():
    if REDIS_URL:
        logger.info('Using Redis cache at %s', REDIS_URL)
        return RedisCache(REDIS_URL)
    logger.info('REDIS_URL not set, using in-process memory cache.')
    return MemoryCache()


# ---------------------------------------------------------------------------
# database
# ---------------------------------------------------------------------------

class Database:
    def __init__(self, cache=None):
        self.cache = cache or make_cache()
        self.client: MongoClient = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]

    # -- collection management ------------------------------------------------
    def ensure_collections(self):
        existing = self.db.list_collection_names()
        for coll in (COLL_FORWARD, COLL_TITLE_INDEX, COLL_CONTENT_INDEX,
                     COLL_DF, COLL_PHRASES, COLL_DOC_STATS):
            if coll not in existing:
                self.db.create_collection(coll)
                logger.info('Created collection %s', coll)

    # -- corpus level ----------------------------------------------------------
    def count_pages(self) -> int:
        cached = self.cache.get('file_num')
        if cached is not None:
            return int(cached)
        n = self.db[COLL_FORWARD].count_documents({})
        self.cache.set('file_num', n)
        return n

    def get_df_map(self, token_ids: list[str] | set[str]) -> dict[str, int]:
        """DF table (cached in full: it only changes when the index changes)."""
        df_map = self.cache.get('df_map')
        if df_map is None:
            df_map = {doc['_id']: doc['df'] for doc in self.db[COLL_DF].find({}, {'df': 1})}
            self.cache.set('df_map', df_map)
        if not token_ids:
            return {}
        return {tid: df_map[tid] for tid in token_ids if tid in df_map}

    def get_phrase_ids(self) -> set[str]:
        phrase_ids = self.cache.get('phrase_ids')
        if phrase_ids is None:
            phrase_ids = {doc['_id'] for doc in self.db[COLL_PHRASES].find({}, {})}
            self.cache.set('phrase_ids', phrase_ids)
        return phrase_ids

    def invalidate_corpus_caches(self):
        for key in _INDEX_CACHE_KEYS:
            self.cache.delete(key)

    # -- inverted index ----------------------------------------------------------
    def get_inverted(self, token_ids: set[str], coll: str) -> dict[str, dict[str, int]]:
        """{tokenId: {url: tf}} for the requested tokens."""
        result: dict[str, dict[str, int]] = {}
        for doc in self.db[coll].find({'_id': {'$in': list(token_ids)}}, {'indexMap': 1}):
            result[doc['_id']] = {
                decode_url(url_key): int(entry['tf'])
                for url_key, entry in doc.get('indexMap', {}).items()
            }
        return result

    def upsert_inverted_entry(self, coll: str, token_id: str, url: str, tf: int) -> int:
        """Insert/update one posting; returns the new inverted-list length (df)."""
        url_key = encode_url(url)
        self.db[coll].update_one(
            {'_id': token_id},
            {'$setOnInsert': {'indexMap': {}}},
            upsert=True,
        )
        self.db[coll].update_one(
            {'_id': token_id},
            {'$set': {f'indexMap.{url_key}': {'url': url, 'tf': tf}}},
        )
        doc = self.db[coll].find_one({'_id': token_id}, {'indexMap': 1})
        return len(doc.get('indexMap', {})) if doc else 0

    def upsert_df(self, token_id: str, df: int):
        self.db[COLL_DF].update_one({'_id': token_id}, {'$set': {'df': df}}, upsert=True)

    # -- phrases -----------------------------------------------------------------
    def upsert_phrase(self, phrase_id: str, df: int):
        self.db[COLL_PHRASES].update_one({'_id': phrase_id}, {'$set': {'df': df}}, upsert=True)

    # -- forward index -------------------------------------------------------------
    def upsert_page(self, page: dict):
        self.db[COLL_FORWARD].update_one({'url': page['url']}, {'$set': page}, upsert=True)

    def get_pages_by_urls(self, urls: list[str]) -> list[dict]:
        return list(self.db[COLL_FORWARD].find({'url': {'$in': urls}}))

    def get_link_graph(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = {}
        for page in self.db[COLL_FORWARD].find({}, {'url': 1, 'childrenLink': 1}):
            graph[page['url']] = set(page.get('childrenLink') or [])
        return graph

    def save_pageranks(self, pagerank: dict[str, float]):
        """Store PageRank normalized relative to the maximum (0..1]."""
        max_pr = max(pagerank.values()) if pagerank else 0
        if max_pr <= 0:
            return
        for url, pr in pagerank.items():
            self.db[COLL_FORWARD].update_one(
                {'url': url}, {'$set': {'pagerank': pr / max_pr}})

    def get_pageranks(self, urls: list[str]) -> dict[str, float]:
        return {
            doc['url']: doc.get('pagerank', 0.0)
            for doc in self.db[COLL_FORWARD].find({'url': {'$in': urls}}, {'url': 1, 'pagerank': 1})
        }

    # -- document statistics (BM25) ------------------------------------------------
    def upsert_doc_stats(self, url: str, title_len: int, content_len: int):
        self.db[COLL_DOC_STATS].update_one(
            {'url': url},
            {'$set': {'url': url, 'title_len': title_len, 'content_len': content_len}},
            upsert=True,
        )

    def avg_field_lengths(self) -> tuple[float, float]:
        """Average title/content length over the whole corpus."""
        pipeline = [{
            '$group': {
                '_id': None,
                'avg_title': {'$avg': '$title_len'},
                'avg_content': {'$avg': '$content_len'},
            }
        }]
        result = list(self.db[COLL_DOC_STATS].aggregate(pipeline))
        if not result:
            return 1.0, 1.0
        return (result[0].get('avg_title') or 1.0, result[0].get('avg_content') or 1.0)
