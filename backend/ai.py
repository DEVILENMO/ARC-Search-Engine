# -*- coding: utf-8 -*-
"""LLM integration.

Three features, one dual-channel backend:
  1. Multi-turn assistant chat with the "弧光天星" persona
  2. Query expansion (LLM proposes synonyms/related words for recall)
  3. RAG-style summary of search results (built by search_engine.py)

Channels: an OpenAI-compatible remote API is tried first; on any failure the
request transparently falls back to a local model served by Ollama, so the
engine keeps working offline / when the key quota is exhausted.
"""
import logging
import re
import threading

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_remote = None   # OpenAI-compatible client (lazy)
_local = None    # Ollama fallback (lazy)


class LLMUnavailableError(RuntimeError):
    """Both the remote API and the local fallback failed."""


# ---------------------------------------------------------------------------
# dual-channel backend
# ---------------------------------------------------------------------------

def _get_remote():
    global _remote
    with _init_lock:
        if _remote is None:
            if not LLM_API_KEY:
                raise LLMUnavailableError('LLM_API_KEY is not configured.')
            from openai import OpenAI
            _remote = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _remote


def _get_local():
    global _local
    with _init_lock:
        if _local is None:
            import ollama
            _local = ollama
    return _local


def _ollama_chat(messages: list[dict]) -> str:
    ollama = _get_local()
    # model is pulled lazily on first use (can take minutes the very first time)
    try:
        ollama.show(OLLAMA_MODEL)
    except Exception:
        logger.info('Pulling local model %s via Ollama (first call only)...', OLLAMA_MODEL)
        ollama.pull(OLLAMA_MODEL)
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response['message']['content']


def chat(messages: list[dict]) -> str:
    """Route a chat completion: remote API first, local Ollama as fallback."""
    try:
        remote = _get_remote()
        completion = remote.chat.completions.create(model=LLM_MODEL, messages=messages)
        return completion.choices[0].message.content
    except Exception as e:
        logger.warning('Remote LLM failed (%s), falling back to local Ollama model...', e)
        try:
            return _ollama_chat(messages)
        except Exception as e2:
            raise LLMUnavailableError(f'remote: {e}; local ollama: {e2}') from e2


# ---------------------------------------------------------------------------
# feature 1: persona assistant
# ---------------------------------------------------------------------------

PERSONA_HISTORY = [
    {
        'role': 'system',
        'content': '你需要扮演ARC搜索引擎的人工智能助手弧光天星，根据用户输入的语言和任务要求给出对应语言的反馈。',
    }
]


def assistant_reply(history: list[dict[str, str]]) -> str:
    """Multi-turn reply; prepends the persona system prompt when absent."""
    if history and history[0].get('role') == 'system':
        messages = history
    else:
        messages = list(PERSONA_HISTORY) + list(history)
    return chat(messages)


# ---------------------------------------------------------------------------
# feature 2: query expansion
# ---------------------------------------------------------------------------

EXPANSION_HISTORY = [
    {
        'role': 'system',
        'content': 'Task: Given the user\'s search query above, please help me with the following:\n'
                   'Expand the keyword list by adding synonyms for each keyword. The additional keywords should have '
                   'the same meaning and compared to the original keywords and help improve the search results.\n'
                   'Please note that the answer you give must be in the same language as the input. If the user '
                   'inputs English, the English expansion word will be returned. If the user enters Chinese, '
                   'the Chinese expansion word will be returned. The same is true for other languages. You should'
                   'check the result, if not in the same language as input, you should give a blank answer.\n'
                   '请尽量给出和输入语言对应语言中简单的词语作为近义词结果，而不要进行无关扩展。\n'
                   '接下来给出示例，请按照示例的回答格式进行回答：\n'
                   'Example 1:\n'
                   'Query: 怎么制作番茄炒蛋\n'
                   'Your answer should be:\n'
                   'Input query is in [Chinese]:\n'
                   'Expanded keywords: 教程, 食谱, 西红柿\n'
                   'Example 2:\n'
                   'Query: How to play OverWatch2\n'
                   'Your answer should be:\n'
                   'Input query is in [English]:\n'
                   'Expanded keywords: tutorial, game, overwatch\n'
                   'Example 3:\n'
                   'Query: 汽车自动驾驶\n'
                   'Your answer should be:\n'
                   'Input query is in [Chinese]:\n'
                   'Expanded keywords: 载具, 交通, 科技, 人工智能\n'
                   'You are forbidden to directly copy the example when dealing with user input query.\n'
                   'You are strictly restrained to reply in the example form.',
    }
]

_EXPANDED_LINE = re.compile(r'Expanded keywords\s*[:：]\s*(.*)', re.IGNORECASE)


def expand_query(query: str) -> list[str]:
    """LLM query expansion with a strict few-shot output format, retried 3x."""
    for _ in range(3):
        words = _ask_for_expansion(query)
        if words:
            return words
    return []


def _ask_for_expansion(query: str) -> list[str]:
    messages = list(EXPANSION_HISTORY) + [
        {'role': 'user', 'content': f'This is the query you should deal with: User query: {query}'}
    ]
    try:
        response = chat(messages)
    except Exception as e:
        logger.error('All LLM backends failed while expanding query "%s": %s', query, e)
        return []
    match = _EXPANDED_LINE.search(response)
    if not match:
        logger.warning('LLM reply does not match the expected format: %s', response[:200])
        return []
    return [kw.strip() for kw in match.group(1).split(',') if kw.strip()]
