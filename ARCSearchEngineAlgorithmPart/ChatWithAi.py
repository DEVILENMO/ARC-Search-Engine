from AIModule import *

DEFAULT_HISTORY = [
    {
        'role': 'system', 'content': '你需要扮演ARC搜索引擎的人工智能助手弧光天星，根据用户输入的语言和任务要求给出对应语言的反馈。'
    }
]


def get_ai_response(input_history: list[dict[str: str]]) -> str:
    if input_history[0]['role'] != 'system':
        extend_history = list(DEFAULT_HISTORY)
        extend_history.extend(input_history)
    else:
        extend_history = input_history
    try:
        ai_response = OpenAIModule().get_response(extend_history)
    except Exception as e:
        print('Using local LLM(LLAMA2) for inference...')
        ai_response = Llama2Module().get_response(extend_history)
    return ai_response
