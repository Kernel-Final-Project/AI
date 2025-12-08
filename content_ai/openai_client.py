# content_ai/openai_client.py

from openai import OpenAI
from utils.load_env import get_env


class OpenAIClient:
    def __init__(self):
        api_key = get_env("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=api_key)

    def generate_text(
        self, system_prompt, user_prompt, model="gpt-4o-mini", temperature=0.7
    ):
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content
