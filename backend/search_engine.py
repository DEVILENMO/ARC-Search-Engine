# -*- coding: utf-8 -*-
"""Retrieval & ranking pipeline (port of the original Java SearchService).

Pipeline:
  query -> pretreat -> ordered BPE tokens -> phrase extraction (query terms)
        -> inverted index lookups (title + content) -> candidate documents
        -> scoring (BM25 or TF-IDF cosine, switchable via SCORE_MODE)
        -> PageRank re-ranking: final = score * (1 + w * pagerank)
        -> forward index lookup -> result DTOs
  async: LLM query expansion (related words) + LLM RAG summary via WebSocket
"""
import logging
import math
from typing import Callable

from config import (BM25_B, BM25_K1, MAX_CONTENT_SNIPPET, PAGERANK_WEIGHT,
                    PHRASE_BOOST, SCORE_MODE, SUMMARY_TOP_RESULTS, TITLE_BOOST,
                    TOP_RESULTS)
from storage import Database

logger = logging.getLogger(__name__)

CUE_WORD_TITLE = 'This is the search query given by the user:'
CUE_WORD_BODY = ('. Please generate a concise summary within 100 words based on both the query and the search '
                 'results, focusing on the key information most relevant to the user\'s query. Strictly exclude any '
                 'advertisement content from the summary. If the search results contain multiple languages, please '
                 'generate the summary in the dominant language of the results. Organize the summary into short '
                 'paragraphs with clear subheadings if applicable.')


def phrase_boost(token_id: str) -> float:
    """Phrases ('-'-joined token ids) are boosted by their word count."""
    if '-' not in token_id:
        return 1.0
    return 1.0 + PHRASE_BOOST * token_id.count('-')


def cosine_similarity(query_weights: dict[str, float], doc_weights: dict[str, float]) -> float:
    """Cosine of the angle between the query vector and a document vector."""
    dot_product = sum(w * doc_weights.get(term, 0.0) for term, w in query_weights.items())
    query_magnitude = math.sqrt(sum(w * w for w in query_weights.values()))
    doc_magnitude = math.sqrt(sum(w * w for w in doc_weights.values()))
    if query_magnitude == 0 or doc_magnitude == 0:
        return 0.0
    return dot_product / (query_magnitude * doc_magnitude)


class SearchEngine:
    def __init__(self, db: Database, tokenizer,
                 submit_task: Callable[[Callable], None] | None = None,
                 broadcast: Callable[[int, dict], None] | None = None):
        """
        :param submit_task: runs a callable in a background worker (async pushes)
        :param broadcast:   sends {type, msg} to every connected WebSocket client
        """
        self.db = db
        self.tokenizer = tokenizer
        self.submit_task = submit_task or (lambda fn: fn())
        self.broadcast = broadcast

    # ------------------------------------------------------------------
    # main entry
    # ------------------------------------------------------------------
    def search(self, keywords: str) -> dict:
        from textproc import extract_phrases, pretreat_text

        query_words = ' '.join(pretreat_text(keywords))
        ordered_ids = self.tokenizer.tokenize_in_order(query_words)
        stems = extract_phrases(ordered_ids, self.db.get_phrase_ids())
        token_ids = set(stems.keys())

        logger.info('Search "%s" -> query tokens: %s', keywords, token_ids)

        title_inv = self.db.get_inverted(token_ids, 'title_index')
        content_inv = self.db.get_inverted(token_ids, 'content_index')
        df_map = self.db.get_df_map(token_ids)
        n_docs = self.db.count_pages()

        # ---- candidate documents ----
        candidates: dict[str, dict] = {}

        def _register(url: str, field: str, token_id: str, tf: int):
            doc = candidates.setdefault(url, {'title': {}, 'content': {}})
            doc[field][token_id] = tf

        for token_id, postings in title_inv.items():
            for url, tf in postings.items():
                _register(url, 'title', token_id, tf)
        for token_id, postings in content_inv.items():
            for url, tf in postings.items():
                _register(url, 'content', token_id, tf)

        if not candidates:
            logger.info('No candidate documents for query "%s".', keywords)
            return {'results': [], 'keywordsTokenId': sorted(token_ids), 'relatedResList': []}

        pages = {page['url']: page for page in self.db.get_pages_by_urls(list(candidates))}
        candidates = {url: data for url, data in candidates.items() if url in pages}

        # ---- scoring ----
        if SCORE_MODE == 'tfidf':
            scores = self._score_tfidf(stems, df_map, n_docs, candidates, pages)
        else:
            field_lengths = self._load_field_lengths(candidates)
            scores = self._score_bm25(stems, df_map, n_docs, candidates, field_lengths)

        # ---- PageRank re-ranking (link analysis on top of text relevance) ----
        pageranks = self.db.get_pageranks(list(candidates))
        ranked = sorted(
            ((url, score * (1.0 + PAGERANK_WEIGHT * pageranks.get(url, 0.0)))
             for url, score in scores.items()),
            key=lambda item: item[1], reverse=True,
        )[:TOP_RESULTS]

        # ---- result DTOs ----
        results = []
        for url, score in ranked:
            page = pages[url]
            content = page.get('content') or ''
            results.append({
                'url': url,
                'title': page.get('title') or url,
                'score': round(float(score), 6),
                'content': content[:MAX_CONTENT_SNIPPET],
                'keywordsFrequency': self._keyword_frequencies(stems, page),
                'parentLinks': page.get('parentLink') or [],
                'childLinks': page.get('childrenLink') or [],
                'img': page.get('img') or '',
                'icon': page.get('icon') or '',
                'pagerank': round(float(pageranks.get(url, 0.0)), 6),
            })

        # ---- async LLM features (do not block the HTTP response) ----
        self.submit_task(lambda: self._push_related_words(keywords))
        self.submit_task(lambda: self._push_summary(keywords, results))

        return {
            'results': results,
            'keywordsTokenId': sorted(token_ids),
            'relatedResList': [],
        }

    # ------------------------------------------------------------------
    # scoring models
    # ------------------------------------------------------------------
    def _score_bm25(self, stems, df_map, n_docs, candidates, field_lengths) -> dict[str, float]:
        """Okapi BM25 with per-field weighting (BM25F-style title boost)."""
        avg_title, avg_content = self.db.avg_field_lengths()
        scores: dict[str, float] = {url: 0.0 for url in candidates}
        for token_id in stems:
            df = df_map.get(token_id, 0)
            if df == 0:
                continue
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            boost = phrase_boost(token_id)
            for url, fields in candidates.items():
                score = 0.0
                title_tf = fields['title'].get(token_id, 0)
                content_tf = fields['content'].get(token_id, 0)
                if title_tf:
                    title_len = field_lengths.get((url, 'title'), 1)
                    score += TITLE_BOOST * idf * (title_tf * (BM25_K1 + 1)) / (
                        title_tf + BM25_K1 * (1 - BM25_B + BM25_B * title_len / avg_title))
                if content_tf:
                    content_len = field_lengths.get((url, 'content'), 1)
                    score += idf * (content_tf * (BM25_K1 + 1)) / (
                        content_tf + BM25_K1 * (1 - BM25_B + BM25_B * content_len / avg_content))
                scores[url] += score * boost
        return scores

    def _score_tfidf(self, stems, df_map, n_docs, candidates, pages) -> dict[str, float]:
        """The original course algorithm: TF-IDF weights + cosine similarity.

        Title terms get a TITLE_BOOST multiplier, phrases get PHRASE_BOOST.
        Document vectors cover every token of the document (correct cosine
        magnitudes); DF values come from the cached DF table.
        """
        # query vector
        query_tf_max = max(stems.values()) if stems else 1
        query_weights: dict[str, float] = {}
        for token_id, tf in stems.items():
            df = df_map.get(token_id, 0)
            if df == 0:
                continue
            idf = math.log(n_docs / df, 2)
            query_weights[token_id] = tf * idf / query_tf_max * phrase_boost(token_id)

        scores: dict[str, float] = {}
        for url, fields in candidates.items():
            doc_weights = self._doc_tfidf_vector(url, fields, pages[url], df_map, n_docs)
            scores[url] = cosine_similarity(query_weights, doc_weights)
        return scores

    def _doc_tfidf_vector(self, url, fields, page, df_map, n_docs) -> dict[str, float]:
        """TF-IDF vector over every token of the document (title merged in)."""
        title_tf = page.get('title_tf') or {}
        content_tf = page.get('content_tf') or {}

        def tf_max(mapping: dict) -> int:
            return max((int(v) for v in mapping.values()), default=1)

        weights: dict[str, float] = {}
        for token_id, tf in title_tf.items():
            df = df_map.get(token_id, 0)
            if df == 0:
                continue
            idf = math.log(n_docs / df, 2)
            weights[token_id] = weights.get(token_id, 0.0) + \
                int(tf) * idf / tf_max(title_tf) * TITLE_BOOST * phrase_boost(token_id)
        for token_id, tf in content_tf.items():
            df = df_map.get(token_id, 0)
            if df == 0:
                continue
            idf = math.log(n_docs / df, 2)
            weights[token_id] = weights.get(token_id, 0.0) + \
                int(tf) * idf / tf_max(content_tf) * phrase_boost(token_id)
        return weights

    def _field_len(self, url: str, field: str) -> int:
        """Document length (token count) for BM25; falls back to query-token tf."""
        return self._field_lens.get((url, field), 1)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _keyword_frequencies(stems, page) -> list[dict]:
        """Combined title+content tf of the query terms, for the result card."""
        title_tf = page.get('title_tf') or {}
        content_tf = page.get('content_tf') or {}
        output = []
        for token_id in sorted(stems):
            total = int(title_tf.get(token_id, 0)) + int(content_tf.get(token_id, 0))
            if total > 0:
                output.append({'tokenId': token_id, 'df': total})
        return output

    def _load_field_lengths(self, candidates) -> dict[tuple[str, str], int]:
        """Candidate document lengths for BM25 normalization (one Mongo query)."""
        urls = list(candidates)
        stats = {doc['url']: doc for doc in self.db.db['doc_stats'].find({'url': {'$in': urls}})}
        lengths: dict[tuple[str, str], int] = {}
        for url in urls:
            stat = stats.get(url)
            title_len = int(stat['title_len']) if stat and stat.get('title_len') else 1
            content_len = int(stat['content_len']) if stat and stat.get('content_len') else 1
            lengths[(url, 'title')] = title_len
            lengths[(url, 'content')] = content_len
        return lengths

    # ------------------------------------------------------------------
    # async LLM features
    # ------------------------------------------------------------------
    def _push_related_words(self, keywords: str):
        if not self.broadcast:
            return
        try:
            from ai import expand_query
            related = {}
            for word in expand_query(keywords):
                token_ids = [str(_) for _ in self.tokenizer.tokenize(word)]
                related[word] = '-'.join(token_ids)
            if related:
                self.broadcast(0, related)
        except Exception:
            logger.exception('Related-word expansion failed for "%s"', keywords)

    def _push_summary(self, keywords: str, results: list[dict]):
        if not self.broadcast:
            return
        try:
            from ai import chat
            prompt = CUE_WORD_TITLE + keywords + CUE_WORD_BODY
            for i, result in enumerate(results[:SUMMARY_TOP_RESULTS], start=1):
                prompt += f'{i}、title:{result["title"]} main body:{result["content"]}'
            summary = chat([{'role': 'user', 'content': prompt.replace('#', ' ')}])
            self.broadcast(1, {'msg': summary})
        except Exception:
            logger.exception('AI summary failed for "%s"', keywords)
