from openai import OpenAI
from utils.load_env import OPENAI_API_KEY
from utils.logger import logger


class OpenAIClient:
    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        try:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
            raise

    def generate_text(self, system_prompt, user_prompt, model="gpt-4o-mini", temperature=0.7):
        """
        텍스트 생성
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            model: 사용할 모델 (기본값: gpt-4o-mini)
            temperature: 온도 설정 (0.0 ~ 2.0)
            
        Returns:
            생성된 텍스트
        """
        try:
            logger.info(f"OpenAI API 호출 시작 (모델: {model})")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            result = response.choices[0].message.content
            logger.info("OpenAI API 호출 성공")
            return result
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            raise