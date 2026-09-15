# -*- coding: utf-8 -*-
"""AI assistant endpoint logic: multi-turn chat with a persona system prompt."""
from AIModule import chat

# 弧光天星: the AI persona of the ARC search engine assistant.
DEFAULT_HISTORY = [
    {
        'role': 'system', 'content': '你需要扮演ARC搜索引擎的人工智能助手弧光天星，根据用户输入的语言和任务要求给出对应语言的反馈。'
    }
]


def get_ai_response(input_history: list[dict[str, str]]) -> str:
    if input_history and input_history[0].get('role') == 'system':
        extend_history = input_history
    else:
        extend_history = list(DEFAULT_HISTORY)
        extend_history.extend(input_history)
    return chat(extend_history)
