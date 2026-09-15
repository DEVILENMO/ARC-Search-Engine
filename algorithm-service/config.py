# -*- coding: utf-8 -*-
"""Central configuration for the ARC algorithm service.

All settings can be overridden through environment variables so that no
secrets (e.g. the LLM API key) are ever committed to the repository.
"""
import os

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
# OpenAI-compatible API. Any endpoint that implements the /v1/chat/completions
# contract works (OpenAI, Azure proxy, vLLM, one-api, ...).
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')

# Local fallback via Ollama, used when the remote API is unavailable.
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2-chinese')

# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8888'))

# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------
# Crawl politely: obey robots.txt ("gentleman's agreement") by default.
FOLLOW_GENTLEMANS_AGREEMENT = os.getenv('CRAWLER_RESPECT_ROBOTS', 'true').lower() != 'false'
CRAWLER_USER_AGENT = os.getenv('CRAWLER_USER_AGENT', 'ARC-Search-Engine-Crawler/1.0')
CRAWLER_TIMEOUT_SECONDS = int(os.getenv('CRAWLER_TIMEOUT_SECONDS', '10'))
