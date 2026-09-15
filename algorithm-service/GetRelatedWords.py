# -*- coding: utf-8 -*-
"""LLM-based query expansion: ask the LLM for synonyms of the user query.

The expanded words are converted to GPT-2 token ids so the Java backend can
look them up in the same inverted index as the original query tokens.
"""
import logging
import re

from AIModule import chat
from BaseModule import SearchEngineTokenizer

logger = logging.getLogger(__name__)

DEFAULT_HISTORY = [
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
                   'You are strictly restrained to reply in the example form.'
    }
]

_EXPANDED_LINE = re.compile(r'Expanded keywords\s*[:：]\s*(.*)', re.IGNORECASE)


def get_related_word(query: str, tokenizer: SearchEngineTokenizer) -> dict[str, str]:
    related_words = []
    for _ in range(3):
        related_words = _extract_expanded_keywords(query)
        if related_words:
            break
    related_word_token_dict = {}
    for word in related_words:
        token_ids = [str(_) for _ in tokenizer.tokenize(word)]
        related_word_token_dict[word] = '-'.join(token_ids)
    return related_word_token_dict


def _extract_expanded_keywords(query: str) -> list[str]:
    history = list(DEFAULT_HISTORY)
    history.append({
        'role': 'user',
        'content': f'This is the query you should deal with: User query: {query}'
    })
    try:
        response = chat(history)
    except Exception as e:
        logger.error('All LLM backends failed while expanding query "%s": %s', query, e)
        return []

    match = _EXPANDED_LINE.search(response)
    if not match:
        logger.warning('LLM reply does not match the expected format: %s', response[:200])
        return []
    return [kw.strip() for kw in match.group(1).split(',') if kw.strip()]


if __name__ == '__main__':
    query = '我想要成为丁真大人那样伟大的人'
    print(get_related_word(query, SearchEngineTokenizer()))
    # {'搞笑': '162-238-252-163-105-239', '网络': '163-121-239-163-119-250', ...}
