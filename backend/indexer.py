# -*- coding: utf-8 -*-
"""Indexing pipeline (port of the original Java PageLinkService).

For every crawled page:
  1. content index  — pretreat(title + content) -> BPE tokens -> Apriori
                      phrase mining -> {tokenId: tf} upserted into content_index
  2. title index    — pretreat(title) -> ordered BPE tokens -> phrase
                      extraction against the known phrase table -> title_index
  3. forward index  — the page document itself (snippet source)
  4. doc_stats      — title/content lengths for BM25
After a batch:
  5. phrases table  — every '-'-joined token id discovered by the miner
  6. parent links   — children links reversed into parentLink sets
  7. PageRank       — power iteration over the link graph, stored 0..1
"""
import logging

from config import PAGERANK_DAMPING, PAGERANK_ITERATIONS
from crawler import SimpleCrawler
from pagerank import compute_pagerank
from textproc import extract_phrases, pretreat_text
from storage import Database, COLL_CONTENT_INDEX, COLL_TITLE_INDEX

logger = logging.getLogger(__name__)


class Indexer:
    def __init__(self, db: Database, tokenizer, crawler_factory=SimpleCrawler):
        self.db = db
        self.tokenizer = tokenizer
        self.crawler_factory = crawler_factory

    # ------------------------------------------------------------------
    # public entry: crawl a start URL then index everything it produced
    # ------------------------------------------------------------------
    def crawl_and_index(self, start_url: str, max_suburl: int, max_depth: int,
                        on_progress=None):
        """on_progress(finish_num, task_num) is called after each page."""
        crawler = self.crawler_factory(start_url, max_depth, max_suburl)
        pages = crawler.crawl()
        self.index_pages(pages, start_url=start_url, on_progress=on_progress)

    def index_pages(self, pages: dict[str, dict], start_url: str, on_progress=None):
        total = len(pages)
        logger.info('Indexing %d pages crawled from %s', total, start_url)
        for i, (url, data) in enumerate(pages.items(), start=1):
            try:
                self.index_single_page(url, data)
            except Exception:
                logger.exception('Failed to index %s', url)
            if on_progress:
                on_progress(i, total)

        self.update_phrases()
        self.update_parent_links()
        self.compute_and_store_pagerank()
        self.db.invalidate_corpus_caches()
        logger.info('Batch from %s fully indexed.', start_url)

    # ------------------------------------------------------------------
    # single page
    # ------------------------------------------------------------------
    def index_single_page(self, url: str, data: dict):
        title = data.get('title') or ''
        content = data.get('content') or ''

        # ---- content inverted index (word count + Apriori phrase mining) ----
        content_tokens = pretreat_text(f'{title} {content}')
        content_index = self.tokenizer.tokenize_disordered_with_word_count(content_tokens)
        article_id = content_index.pop('ARTICLE_ID', '')
        for token_id, tf in content_index.items():
            df = self.db.upsert_inverted_entry(COLL_CONTENT_INDEX, token_id, url, int(tf))
            self.db.upsert_df(token_id, df)

        # ---- title inverted index (ordered tokens + known phrase lookup) ----
        title_tokens = pretreat_text(title)
        ordered_title_ids = self.tokenizer.tokenize_in_order(' '.join(title_tokens))
        title_index = extract_phrases(ordered_title_ids, self.db.get_phrase_ids())
        title_tf_sums: dict[str, int] = {}
        for token_id, tf in title_index.items():
            df = self.db.upsert_inverted_entry(COLL_TITLE_INDEX, token_id, url, int(tf))
            self.db.upsert_df(token_id, df)
            title_tf_sums[token_id] = int(tf)

        # ---- forward index + doc stats ----
        self.db.upsert_page({
            'url': url,
            'title': title,
            'content': content,
            'title_tf': title_tf_sums,
            'content_tf': dict(content_index),
            'icon': data.get('icon') or '',
            'img': data.get('main_image') or '',
            'articleId': article_id,
            'childrenLink': list(data.get('sublinks') or []),
        })
        self.db.upsert_doc_stats(
            url,
            title_len=sum(title_tf_sums.values()),
            content_len=sum(int(v) for v in content_index.values()),
        )

    # ------------------------------------------------------------------
    # batch maintenance
    # ------------------------------------------------------------------
    def update_phrases(self):
        """Every '-'-joined token id found by the miner becomes a phrase entry."""
        regex = {'$regex': r'.*-.*'}
        count = 0
        for coll in (COLL_TITLE_INDEX, COLL_CONTENT_INDEX):
            for doc in self.db.db[coll].find({'_id': regex}, {'indexMap': 1}):
                self.db.upsert_phrase(doc['_id'], len(doc.get('indexMap', {})))
                count += 1
        logger.info('Phrase table updated (%d phrase postings).', count)

    def update_parent_links(self):
        """Reverse childrenLink into parentLink (fixes the original NPE/wrong-url bug)."""
        pages = self.db.db['forward_index'].find({}, {'url': 1, 'childrenLink': 1})
        graph: dict[str, set[str]] = {}
        for page in pages:
            graph[page['url']] = set(page.get('childrenLink') or [])

        parents: dict[str, set[str]] = {}
        for parent_url, children in graph.items():
            for child_url in children:
                if child_url in graph:
                    parents.setdefault(child_url, set()).add(parent_url)

        for child_url, parent_set in parents.items():
            self.db.db['forward_index'].update_one(
                {'url': child_url}, {'$set': {'parentLink': sorted(parent_set)}})
        logger.info('Parent links updated for %d pages.', len(parents))

    def compute_and_store_pagerank(self):
        graph = self.db.get_link_graph()
        if not graph:
            return
        pagerank = compute_pagerank(graph, damping=PAGERANK_DAMPING, iterations=PAGERANK_ITERATIONS)
        self.db.save_pageranks(pagerank)
        top = sorted(pagerank.items(), key=lambda kv: kv[1], reverse=True)[:3]
        logger.info('PageRank stored. Top pages: %s', [(u[:60], round(p, 4)) for u, p in top])


# ----------------------------------------------------------------------
# query-side phrase extraction lives in textproc (shared with search)
# ----------------------------------------------------------------------
