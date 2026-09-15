# -*- coding: utf-8 -*-
"""LLM backends.

`chat()` tries the OpenAI-compatible remote API first and transparently
falls back to a local model served by Ollama, so that the search engine
keeps working (offline / rate-limited / key quota exhausted).
"""
import logging
import threading

from openai import OpenAI

from BaseModule import AIModule
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_openai_module: OpenAIModule | None = None
_local_module: LlamaModule | None = None


class OpenAIModule(AIModule):
    def __init__(self):
        if not LLM_API_KEY:
            raise RuntimeError('LLM_API_KEY is not configured. Set the environment variable or use the local Ollama fallback.')
        self.client = OpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
        )
        self.model = LLM_MODEL

    def get_response(self, input_history: list[dict[str, str]]) -> str:
        chat_completion = self.client.chat.completions.create(
            messages=input_history,
            model=self.model,
        )
        return chat_completion.choices[0].message.content


class LlamaModule(AIModule):
    """Local fallback backed by Ollama. The model is pulled lazily on first use."""

    def __init__(self):
        import ollama
        self.ollama = ollama
        self.model_name = OLLAMA_MODEL
        self._model_ready = False

    def _ensure_model(self):
        if not self._model_ready:
            logger.info('Pulling local model %s via Ollama (first call only)...', self.model_name)
            self.ollama.pull(self.model_name)
            self._model_ready = True

    def get_response(self, input_history: list[dict[str, str]]) -> str:
        self._ensure_model()
        response = self.ollama.chat(model=self.model_name, messages=input_history)
        return response['message']['content']


def chat(input_history: list[dict[str, str]]) -> str:
    """Route a chat request: remote API first, local Ollama as fallback."""
    global _openai_module, _local_module
    with _init_lock:
        if _openai_module is None:
            _openai_module = OpenAIModule()
        if _local_module is None:
            _local_module = LlamaModule()

    try:
        return _openai_module.get_response(input_history)
    except Exception as e:
        logger.warning('Remote LLM request failed (%s), falling back to local LLM...', e)
        return _local_module.get_response(input_history)


if __name__ == '__main__':
    print(chat([
        {
            'role': 'user',
            'content': '你好，你是谁？'
        }
    ]))
