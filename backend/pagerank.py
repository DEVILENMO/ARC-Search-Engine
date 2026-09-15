# -*- coding: utf-8 -*-
"""PageRank over the crawled link graph (power iteration).

The graph is built by the indexer from parent/child links. Edges pointing
outside the crawled corpus are ignored, and dangling nodes (no outbound
links inside the corpus) redistribute their rank uniformly — the standard
treatment from the original Page & Brin paper.
"""
import logging

from config import PAGERANK_DAMPING, PAGERANK_ITERATIONS

logger = logging.getLogger(__name__)


def compute_pagerank(graph: dict[str, set[str]],
                     damping: float = PAGERANK_DAMPING,
                     iterations: int = PAGERANK_ITERATIONS) -> dict[str, float]:
    """Return {url: pagerank} with values summing to 1.0."""
    urls = list(graph.keys())
    n = len(urls)
    if n == 0:
        return {}

    index_of = {url: i for i, url in enumerate(urls)}
    out_links: list[list[int]] = []
    for url in urls:
        targets = {index_of[c] for c in graph.get(url, ()) if c in index_of}
        out_links.append(sorted(targets))

    rank = [1.0 / n] * n
    for _ in range(iterations):
        new_rank = [(1.0 - damping) / n] * n
        dangling_mass = 0.0
        for i, targets in enumerate(out_links):
            if targets:
                share = damping * rank[i] / len(targets)
                for j in targets:
                    new_rank[j] += share
            else:
                dangling_mass += rank[i]
        dangling_share = damping * dangling_mass / n
        rank = [value + dangling_share for value in new_rank]

    result = {url: rank[i] for i, url in enumerate(urls)}
    logger.info('PageRank converged over %d nodes.', n)
    return result
