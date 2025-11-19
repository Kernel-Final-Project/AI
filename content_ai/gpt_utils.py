"""
GPT 관련 공통 유틸리티 함수
AI2 담당
"""
import time
import json
from typing import Optional
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
    OpenAIError,
    BadRequestError
)
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


def call_gpt(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_retries: int = 3,
) -> Optional[str]:
    """
    GPT 호출 공통 유틸 함수 (예외 처리 + 재시도 로직)
    
    Args:
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        model: 사용할 모델 (기본값: gpt-4o-mini)
        temperature: 온도 설정 (0.0 ~ 2.0, 기본값: 0.7)
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 텍스트 (실패 시 None)
    """
    client = get_client()  # 싱글톤 패턴 유지
    
    for attempt in range(max_retries):
        try:
            result = client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
            )
            
            if isinstance(result, str):
                return result.strip()
            return json.dumps(result, ensure_ascii=False)
            
        except RateLimitError:
            wait_time = 3 * (attempt + 1)  # 지수 백오프
            logger.warning(f"[RateLimitError] {wait_time}초 대기 후 재시도 ({attempt+1}/{max_retries})")
            time.sleep(wait_time)
            continue
            
        except APIConnectionError:
            wait_time = 2 * (attempt + 1)
            logger.warning(f"[ConnectionError] 네트워크 문제. {wait_time}초 후 재시도 ({attempt+1}/{max_retries})")
            time.sleep(wait_time)
            continue
            
        except BadRequestError as e:
            logger.error(f"[InvalidRequest] 요청이 너무 큼(토큰 초과): {e}")
            return None
            
        except AuthenticationError:
            logger.error("[AuthError] API Key 인증 실패. OPENAI_API_KEY 확인 필요.")
            return None
            
        except OpenAIError as e:
            logger.error(f"[OpenAIError] 기타 오류: {e}")
            return None
            
        except Exception as e:
            logger.error(f"[Unexpected ERROR] 예측 못한 오류: {e}")
            return None
    
    logger.error(f"[실패] 최대 재시도 횟수({max_retries}) 초과로 GPT 호출 실패")
    return None


def generate_with_prompt(
    prompt_name: str,
    user_data: dict,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_retries: int = 3
) -> Optional[str]:
    """
    프롬프트 파일을 사용하여 텍스트 생성 (재시도 로직 포함)
    
    Args:
        prompt_name: 프롬프트 파일명 (확장자 제외, 예: "title_prompt")
        user_data: user_prompt에 삽입할 데이터 딕셔너리
        model: 사용할 모델 (기본값: gpt-4o-mini)
        temperature: 온도 설정 (0.0 ~ 2.0, 기본값: 0.7)
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 텍스트 (실패 시 None)
    """
    system_prompt = load_prompt(prompt_name)
    user_prompt = "\n".join([f"{k}: {v}" for k, v in user_data.items()])
    
    return call_gpt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_retries=max_retries
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

