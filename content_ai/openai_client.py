# content_ai/openai_client.py

from openai import OpenAI
from utils.load_env import OPENAI_API_KEY


class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

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
        return response.choices[0].message["content"]
