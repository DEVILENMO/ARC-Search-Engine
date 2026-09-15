# -*- coding: utf-8 -*-
"""Integration test for the ARC backend without network/LLM dependencies.

Runs the indexing + retrieval pipeline against mongomock (an in-memory
pymongo stand-in) with synthetic page data, then drives the FastAPI routes
through the Starlette TestClient (WebSocket included).

Usage: python test_integration.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mongomock
from pymongo import MongoClient

import storage
from storage import Database
from tokenizer import SearchEngineTokenizer

PASS = 0
FAIL = 0


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {name}')
    else:
        FAIL += 1
        print(f'  [FAIL] {name} {detail}')


def make_database() -> Database:
    client = mongomock.MongoClient()
    db = Database.__new__(Database)
    db.cache = storage.MemoryCache()
    db.client = client
    db.db = client['ARC_ENGINE']
    return db


# ---------------------------------------------------------------------------
# 1. unit-ish: pure functions
# ---------------------------------------------------------------------------
print('\n== pagerank ==')
from pagerank import compute_pagerank

graph = {
    'http://a': {'http://b', 'http://c'},
    'http://b': {'http://c'},
    'http://c': set(),
}
pr = compute_pagerank(graph, iterations=50)
check('pagerank sums to 1', abs(sum(pr.values()) - 1.0) < 1e-6, str(pr))
check('c ranks highest (most in-links)', pr['http://c'] > pr['http://a'] and pr['http://c'] > pr['http://b'], str(pr))
check('empty graph safe', compute_pagerank({}) == {})

print('\n== textproc ==')
from textproc import extract_phrases, longest_common_substring, pretreat_text

# 前导空格由分词器内部strip处理，这里只验证切分与大小写
check('pretreat lowercases + splits', pretreat_text('Hello, World! 赛博') == ['hello', ' world', ' 赛博'],
      str(pretreat_text('Hello, World! 赛博')))
check('LCS', longest_common_substring('12345-678', '12345-999') == 6)

phrases = {'100-200-300'}
res = extract_phrases(['100', '200', '300', '400'], phrases)
check('known phrase extracted', '100-200-300' in res, str(res))
check('single tokens kept alongside', '400' in res, str(res))
check('tokens covered by phrase dropped', '100' not in res and '200' not in res, str(res))

print('\n== tokenizer ==')
tokenizer = SearchEngineTokenizer()
disordered = tokenizer.tokenize_disordered_with_word_count([
    ' 赛博朋克2077真好玩',
    ' 赛博朋克 怎么赚钱',
    '我想下载赛博 朋克 ',
    'steam赛博朋克售价',
    '赛博朋克 鬼畜',
    '赛 博 朋 克 真 好 玩',
    '【赛博朋克2077】这游戏bug真多',
])
check('phrase mining finds phrases', any('-' in k for k in disordered if k != 'ARTICLE_ID'),
      str(disordered))
check('ARTICLE_ID present', 'ARTICLE_ID' in disordered)
ordered = tokenizer.tokenize_in_order('How to play Overwatch')
check('ordered tokenization returns id list',
      isinstance(ordered, list) and len(ordered) > 0 and all(isinstance(t, str) for t in ordered),
      str(ordered))

# ---------------------------------------------------------------------------
# 2. integration: index pages, then search
# ---------------------------------------------------------------------------
print('\n== indexer + search pipeline ==')
from indexer import Indexer
from search_engine import SearchEngine

db = make_database()
db.ensure_collections()
indexer = Indexer(db, tokenizer)


def page(title, content, sublinks=()):
    return {'title': title, 'content': content, 'icon': '', 'main_image': '',
            'sublinks': list(sublinks)}


pages = {
    'http://a.com/overwatch': page('Overwatch2 Guide', 'How to play Overwatch2. Overwatch2 is a shooter game.',
                                   ['http://a.com/news', 'http://b.com/other']),
    'http://a.com/news': page('Overwatch2 News', 'Overwatch2 season news and patch notes.', ['http://a.com/overwatch']),
    'http://b.com/other': page('Cyberpunk 2077', 'Cyberpunk 2077 is an open world RPG game with bugs.'),
    'http://b.com/empty': page('', ''),
}
progress_calls = []


def on_progress(done, total):
    progress_calls.append((done, total))


indexer.index_pages(pages, start_url='http://a.com', on_progress=on_progress)

check('progress reported per page', len(progress_calls) == 4 and progress_calls[-1] == (4, 4),
      str(progress_calls))
check('forward index populated', db.db['forward_index'].count_documents({}) == 4)
check('inverted indexes populated',
      db.db['title_index'].count_documents({}) > 0 and db.db['content_index'].count_documents({}) > 0)
check('df table populated', db.db['stem_df'].count_documents({}) > 0)
check('corpus cache invalidated', db.cache.get('file_num') is None)

# parent links: a.com/overwatch <-> a.com/news are mutual children
news = db.db['forward_index'].find_one({'url': 'http://a.com/news'})
overwatch_page = db.db['forward_index'].find_one({'url': 'http://a.com/overwatch'})
check('parent links reversed', 'http://a.com/overwatch' in (news.get('parentLink') or []),
      str(news.get('parentLink')))
check('pagerank stored', isinstance(overwatch_page.get('pagerank'), float) and overwatch_page['pagerank'] > 0,
      str(overwatch_page.get('pagerank')))


ws_messages = []
engine = SearchEngine(db, tokenizer,
                      submit_task=lambda fn, *a, **k: fn(*a, **k),
                      broadcast=lambda t, m: ws_messages.append((t, m)))

# stub the LLM layer so the async push path is deterministic in tests
import ai
ai.chat = lambda messages: 'Input query is in [English]:\nExpanded keywords: guide, tutorial'

result = engine.search('How to play Overwatch2')
check('search returns results', len(result['results']) > 0, json.dumps(result)[:300])
check('results ranked by score desc',
      all(result['results'][i]['score'] >= result['results'][i + 1]['score']
          for i in range(len(result['results']) - 1)))
check('result fields complete', all(
    k in result['results'][0] for k in
    ('url', 'title', 'score', 'content', 'keywordsFrequency', 'parentLinks', 'childLinks', 'img', 'icon')))
check('keyword frequency non-empty', len(result['results'][0]['keywordsFrequency']) > 0,
      str(result['results'][0]['keywordsFrequency']))
check('LLM pushes attempted (related words + summary)',
      [t for t, _ in ws_messages] == [0, 1], str([(t, str(m)[:40]) for t, m in ws_messages]))

# BM25 vs TF-IDF both produce sane orderings
import search_engine as se
old_mode = se.SCORE_MODE
se.SCORE_MODE = 'tfidf'
result_tfidf = engine.search('Overwatch2')
se.SCORE_MODE = old_mode
check('tfidf mode works too', len(result_tfidf['results']) > 0 and
      result_tfidf['results'][0]['url'] == 'http://a.com/overwatch',
      str([(r['url'], r['score']) for r in result_tfidf['results']]))

check('empty index safe', engine.search('zzzqqqxxx nonexistent')['results'] == [])

print('\n== storage unit conversions ==')
from storage import decode_url, encode_url

check('url encoding roundtrip', decode_url(encode_url('http://a.b.c/x')) == 'http://a.b.c/x')

# ---------------------------------------------------------------------------
# 3. API routes via TestClient
# ---------------------------------------------------------------------------
print('\n== FastAPI routes ==')
from fastapi.testclient import TestClient

import main as main_module


class _RecordingPool:
    """Records submitted jobs instead of executing them (no network in tests)."""

    def __init__(self):
        self.jobs = []

    def submit(self, fn, *a, **k):
        self.jobs.append((fn, a, k))


# inject mongomock-backed components; TestClient without context manager does
# NOT run the lifespan, so these globals stay in place
pool = _RecordingPool()
main_module.db = db
main_module.engine = engine
main_module.indexer = indexer
main_module.executor = pool

client = TestClient(main_module.app)

r = client.get('/health')
check('GET /health', r.status_code == 200 and r.json()['status'] == 'ok' and r.json()['pages'] == 4, r.text)

r = client.post('/search/get', json={'keywords': 'Overwatch2'})
check('POST /search/get', r.status_code == 200 and len(r.json()['results']) > 0, r.text[:200])
check('response carries relatedResList for frontend', r.json().get('relatedResList') == [])

r = client.post('/PageLink/Parse', json={'urls': 'https://example.com 10, https://other.org'})
check('POST /PageLink/Parse accepts', r.status_code == 200 and r.json() == 2, r.text)
check('crawl jobs queued', len(pool.jobs) == 2, str(len(pool.jobs)))

r = client.post('/AIChat/getReply', json={'sessionId': 'test', 'userQuery': 'hi'})
check('POST /AIChat/getReply (stubbed LLM)', r.status_code == 200 and 'Expanded keywords' in r.text, r.text[:120])
stored = main_module.db.cache.get('chat_test')
check('chat memory has user+assistant turns', stored and len(stored) == 2
      and stored[0]['role'] == 'user' and stored[1]['role'] == 'assistant', str(stored))

# without any LLM backend the endpoint must fail with 502
real_chat = ai.chat
ai.chat = lambda messages: (_ for _ in ()).throw(ai.LLMUnavailableError('down'))
try:
    r = client.post('/AIChat/getReply', json={'sessionId': 'test2', 'userQuery': 'hi'})
    check('AIChat without LLM backend -> 502', r.status_code == 502, str(r.status_code))
finally:
    ai.chat = real_chat

# chat memory write path (bypassing the LLM call itself)
main_module.db.cache.set('chat_test', [{'role': 'user', 'content': 'hi'}], ttl_seconds=60)
check('chat memory persisted', main_module.db.cache.get('chat_test') is not None)

with client.websocket_connect('/websocket') as ws:
    check('WebSocket connects', ws is not None)

asyncio.run(main_module.manager.broadcast(0, {'word': '1-2-3'}))
check('broadcast with no clients does not raise', True)

print(f'\n{"=" * 40}\nPASS: {PASS}  FAIL: {FAIL}')
sys.exit(1 if FAIL else 0)
