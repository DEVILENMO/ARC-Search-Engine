# -*- coding: utf-8 -*-
"""ARC Search Engine - unified backend configuration.

Everything is driven by environment variables so that no secrets and no
machine-specific settings are ever committed to the repository.
"""
import os

# ---------------------------------------------------------------------------
# HTTP service
# ---------------------------------------------------------------------------
# Port 8899 is kept from the original Java backend so the Vue frontend works
# unchanged (it calls http://localhost:8899 and ws://127.0.0.1:8899/websocket).
SERVICE_HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8899'))

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'ARC_ENGINE')

# Redis is OPTIONAL: when REDIS_URL is set it is used for caching and chat
# memory, otherwise an in-process cache is used (zero-dependency dev mode).
REDIS_URL = os.getenv('REDIS_URL', '')

# ---------------------------------------------------------------------------
# Retrieval / ranking
# ---------------------------------------------------------------------------
# Ranking model: "bm25" (default) or "tfidf" (the original course algorithm).
SCORE_MODE = os.getenv('SCORE_MODE', 'bm25').lower()
BM25_K1 = float(os.getenv('BM25_K1', '1.5'))
BM25_B = float(os.getenv('BM25_B', '0.75'))

TOP_RESULTS = int(os.getenv('TOP_RESULTS', '50'))
MAX_CONTENT_SNIPPET = int(os.getenv('MAX_CONTENT_SNIPPET', '300'))
TITLE_BOOST = float(os.getenv('TITLE_BOOST', '10.0'))   # title matches weigh N times more
PHRASE_BOOST = 2.0                                       # each phrase gets boosted by PHRASE_BOOST * hyphen-count
PAGERANK_WEIGHT = float(os.getenv('PAGERANK_WEIGHT', '1.0'))  # final = score * (1 + w * pagerank)
PAGERANK_DAMPING = float(os.getenv('PAGERANK_DAMPING', '0.85'))
PAGERANK_ITERATIONS = int(os.getenv('PAGERANK_ITERATIONS', '30'))

# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------
CRAWLER_MAX_DEPTH = int(os.getenv('CRAWLER_MAX_DEPTH', '3'))
CRAWLER_MAX_WORKERS = int(os.getenv('CRAWLER_MAX_WORKERS', '4'))
CRAWLER_RESPECT_ROBOTS = os.getenv('CRAWLER_RESPECT_ROBOTS', 'true').lower() != 'false'
CRAWLER_USER_AGENT = os.getenv('CRAWLER_USER_AGENT', 'ARC-Search-Engine-Crawler/1.0')
CRAWLER_TIMEOUT_SECONDS = int(os.getenv('CRAWLER_TIMEOUT_SECONDS', '10'))

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
# OpenAI-compatible remote API with automatic fallback to a local Ollama model.
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2-chinese')

# Summary/conclusion is generated from the top-N search results (RAG style).
SUMMARY_TOP_RESULTS = int(os.getenv('SUMMARY_TOP_RESULTS', '5'))

# Chat memory TTL in seconds (per session).
CHAT_MEMORY_TTL_SECONDS = int(os.getenv('CHAT_MEMORY_TTL_SECONDS', '3600'))
