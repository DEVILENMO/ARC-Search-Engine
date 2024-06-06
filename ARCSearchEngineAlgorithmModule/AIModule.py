# -*- coding: utf-8 -*-
import ollama
from openai import OpenAI

from BaseModule import AIModule

from config import LLM_API_KEY


class OpenAIModule(AIModule):
    def __init__(self):
        self.client = OpenAI(
            base_url='https://api.openai-proxy.org/v1',
            api_key=LLM_API_KEY,
        )

    def get_response(self, input_history: list[dict[str: str]]) -> str:
        chat_completion = self.client.chat.completions.create(
            messages=input_history,
            model="gpt-3.5-turbo",
        )
        response_content = chat_completion.choices[0].message.content
        return response_content


class Llama2Module(AIModule):
    def __init__(self):
        self.model_name = 'llama2-chinese'
        ollama.pull(self.model_name)

    def get_response(self, input_history: list[dict[str: str]]) -> str:
        # 调用 ollama.chat 接口,传入聊天历史
        response = ollama.chat(model=self.model_name, messages=input_history)

        # 将 AI 的响应添加到聊天历史
        ai_response = response['message']['content']
        return ai_response


if __name__ == '__main__':
    ai_module = OpenAIModule()
    print(ai_module.get_response([
        {
            "role": "user",
            "content": "你好，你是谁？"
        }
    ]))
