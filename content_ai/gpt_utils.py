"""
GPT 관련 공통 유틸리티 함수
AI2 담당
"""
from content_ai.openai_client import OpenAIClient
from content_ai.prompt_builder import load_prompt
from utils.logger import logger

# 클라이언트 인스턴스 (모듈 레벨, 싱글톤 패턴)
_client = None


def get_client():
    """
    OpenAI 클라이언트 인스턴스 가져오기 (싱글톤 패턴)
    
    Returns:
        OpenAIClient 인스턴스
    """
    global _client
    if _client is None:
        try:
            _client = OpenAIClient()
            logger.info("OpenAI 클라이언트 준비 완료")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
            raise
    return _client


def generate_with_prompt(
    prompt_name: str,
    user_data: dict,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> str:
    """
    프롬프트 파일을 사용하여 텍스트 생성 (공통 함수)
    
    Args:
        prompt_name: 프롬프트 파일명 (확장자 제외, 예: "title_prompt")
        user_data: user_prompt에 삽입할 데이터 딕셔너리
        model: 사용할 모델 (기본값: gpt-4o-mini)
        temperature: 온도 설정 (0.0 ~ 2.0, 기본값: 0.7)
        
    Returns:
        생성된 텍스트
    """
    client = get_client()
    system_prompt = load_prompt(prompt_name)
    
    # user_data를 문자열로 변환
    user_prompt = "\n".join([f"{k}: {v}" for k, v in user_data.items()])
    
    return client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature
    )


def parse_json_response(response: str) -> dict:
    """
    JSON 형식의 응답을 파싱 (공통 함수)
    
    Args:
        response: JSON 문자열
        
    Returns:
        파싱된 딕셔너리 (파싱 실패 시 {"raw": response} 반환)
    """
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 파싱 실패, 원본 반환: {e}")
        return {"raw": response}

