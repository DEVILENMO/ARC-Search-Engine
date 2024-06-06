from AIModule import *
from Tokenizer import *

DEFAULT_HITSTORY = [
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
}]


def get_related_word(query: str, tokenizer: SearchEngineTokenizerGPT2) -> dict[str, str]:
    i = 0
    related_words = []
    while i < 3 and not len(related_words):
        related_words = __get_related_word(query)
        i += 1
    related_word_token_dict = {}
    for word in related_words:
        token_ids = [str(_) for _ in tokenizer.tokenize(word)]
        related_word_token_dict[word] = '-'.join(token_ids)
    return related_word_token_dict


def __get_related_word(query: str) -> list[str]:
    history = list(DEFAULT_HITSTORY)
    history.append({
        'role': 'user',
        'content': f'This is the query you should deal with: User query: {query}'
    })
    try:
        response = OpenAIModule().get_response(history)
    except Exception as e:
        print('Using local LLM(LLAMA2) for inference...')
        response = Llama2Module().get_response(history)
    lines = response.strip().split('\n')
    expanded_keywords = []

    for line in lines:
        if line.startswith('Expanded keywords'):
            expanded_keywords = [kw.strip() for kw in line.split(':')[1].split(',')]
    return expanded_keywords


if __name__ == '__main__':
    input = '我想要成为丁真大人那样伟大的人'
    print(get_related_word(input, SearchEngineTokenizerGPT2()))
    # {'搞笑': '162-238-252-163-105-239', '网络': '163-121-239-163-119-250', '文化': '23877-229-44293-244', '流行语言': '38184-223-26193-234-46237-255-164-101-222'}
