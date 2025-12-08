"""
본문 생성 모듈
AI2 담당
"""
import time
import re
from typing import Dict, Optional
from content_ai.gpt_utils import generate_with_prompt
from content_ai.prompt_builder import format_outline_for_prompt
from utils.logger import logger


def generate_body(keyword: str, title: str, outline: Dict, product_info: str = "", max_retries: int = 3) -> Optional[str]:
    """
    GPT로 본문 생성 (재시도 로직 포함)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        HTML 형식의 본문 (실패 시 None)
    """
    logger.info(f"본문 생성 시작: {keyword} - {title}")
    
    for attempt in range(max_retries):
        try:
            # 아웃라인을 읽기 쉬운 형식으로 변환
            outline_text = format_outline_for_prompt(outline)
            
            # GPT 호출 (content_prompt.txt 사용)
            response = generate_with_prompt(
                prompt_name="content_prompt",
                user_data={
                    "키워드": keyword,
                    "제목": title,
                    "아웃라인": outline_text,
                    "상품 정보": product_info if product_info else "없음"
                },
                temperature=0.7,
                max_retries=2
            )
            
            if not response:
                logger.warning(f"GPT 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            
            # GPT 원본 응답 로그 (처음 500자)
            logger.info(f"GPT 원본 응답 (시도 {attempt+1}):\n{response[:500]}...")
            
            # 본문 상세 정보 로그
            text_only = re.sub(r'<[^>]+>', '', response)
            text_length = len(text_only.strip())
            h2_count = response.count("<h2>") + response.count("<h2 ")
            h3_count = response.count("<h3>") + response.count("<h3 ")
            logger.info(f"생성된 본문 상세: 텍스트 {text_length}자, 전체 {len(response)}자, h2 {h2_count}개, h3 {h3_count}개")
            
            # 본문 검증
            if validate_body(response):
                logger.info(f"본문 생성 완료: {len(response)}자")
                return response
            else:
                # 글자수 초과 시 요약 시도
                text_only = re.sub(r'<[^>]+>', '', response)
                text_length = len(text_only.strip())
                
                if text_length > 1800:
                    logger.info(f"본문 글자수 초과 ({text_length}자). 요약 시도...")
                    summarized = summarize_body(response)
                    if summarized:
                        # 요약 결과 검증 (1800~2100자 범위)
                        summarized_text_only = re.sub(r'<[^>]+>', '', summarized)
                        summarized_length = len(summarized_text_only.strip())
                        
                        if 1800 <= summarized_length <= 2100:
                            # 요약 성공: 1800~2100자 범위
                            if validate_body(summarized, is_summarized=True):
                                logger.info(f"요약 완료: {summarized_length}자 (1800~2100자 범위)")
                                return summarized
                            else:
                                logger.warning(f"요약된 본문 검증 실패. 재시도 ({attempt+1}/{max_retries})")
                        elif summarized_length < 1800:
                            # 요약 후 1800자 미만: 그대로 반환 (재생성하지 않음)
                            logger.info(f"요약 완료: {summarized_length}자 (1800자 미만이지만 그대로 반환)")
                            return summarized
                        else:
                            # 요약 후 2100자 초과: 재요약 시도
                            logger.warning(f"요약 후 글자수 초과 ({summarized_length}자). 재요약 시도...")
                            re_summarized = summarize_body(summarized)
                            if re_summarized:
                                re_summarized_text_only = re.sub(r'<[^>]+>', '', re_summarized)
                                re_summarized_length = len(re_summarized_text_only.strip())
                                if 1800 <= re_summarized_length <= 2100:
                                    if validate_body(re_summarized, is_summarized=True):
                                        logger.info(f"재요약 완료: {re_summarized_length}자")
                                        return re_summarized
                                    else:
                                        logger.warning(f"재요약된 본문 검증 실패. 재시도 ({attempt+1}/{max_retries})")
                                else:
                                    logger.warning(f"재요약 후에도 범위 벗어남 ({re_summarized_length}자). 재시도 ({attempt+1}/{max_retries})")
                            else:
                                logger.warning(f"재요약 실패. 재시도 ({attempt+1}/{max_retries})")
                    else:
                        logger.warning(f"요약 실패. 재시도 ({attempt+1}/{max_retries})")
                else:
                    logger.warning(f"본문 검증 실패. 재시도 ({attempt+1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
                
        except Exception as e:
            logger.error(f"본문 생성 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"본문 생성 실패: 최대 재시도 횟수({max_retries}) 초과")
    return None


def summarize_body(content: str, max_retries: int = 2) -> Optional[str]:
    """
    본문을 요약합니다 (summarize_prompt.txt 사용)
    
    Args:
        content: 원본 본문 HTML
        max_retries: 최대 재시도 횟수 (기본값: 2)
        
    Returns:
        요약된 본문 HTML (실패 시 None)
    """
    logger.info("본문 요약 시작")
    
    for attempt in range(max_retries):
        try:
            # GPT 호출 (summarize_prompt.txt 사용)
            response = generate_with_prompt(
                prompt_name="summarize_prompt",
                user_data={
                    "원본 본문": content
                },
                temperature=0.7,
                max_retries=2
            )
            
            if not response:
                logger.warning(f"요약 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            
            # 요약 결과 검증 (1800~2100자)
            text_only = re.sub(r'<[^>]+>', '', response)
            text_length = len(text_only.strip())
            
            if 1800 <= text_length <= 2100:
                logger.info(f"요약 완료: {text_length}자")
                return response
            else:
                logger.warning(f"요약 글자수 범위 벗어남: {text_length}자 (요구: 1800~2100자). 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
                
        except Exception as e:
            logger.error(f"요약 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"요약 실패: 최대 재시도 횟수({max_retries}) 초과")
    return None


def validate_body(body: str, is_summarized: bool = False) -> bool:
    """
    생성된 본문 검증
    
    Args:
        body: 생성된 본문 HTML
        is_summarized: 요약된 본문인지 여부 (기본값: False)
        
    Returns:
        검증 통과 여부
    """
    if not body or len(body.strip()) == 0:
        logger.warning("본문이 비어있습니다.")
        return False
    
    # 1. h2 태그 포함 여부 확인
    if "<h2>" not in body and "<h2 " not in body:
        logger.warning("본문에 h2 태그가 없습니다.")
        return False
    
    # 2. 글자수 검증
    # HTML 태그 제거하고 순수 텍스트만 계산
    text_only = re.sub(r'<[^>]+>', '', body)
    text_length = len(text_only.strip())
    
    if is_summarized:
        # 요약된 본문: 1800~2100자 범위
        if text_length < 1800:
            logger.warning(f"요약된 본문 글자수 부족: {text_length}자 (요구: 1800자 이상)")
            return False
        
        if text_length > 2100:
            logger.warning(f"요약된 본문 글자수 초과: {text_length}자 (요구: 2100자 이하)")
            return False
        
        logger.debug(f"요약된 본문 검증 통과: {text_length}자")
        return True
    else:
        # 일반 본문: 1500~1800자 범위
        if text_length < 1500:
            logger.warning(f"본문 글자수 부족: {text_length}자 (요구: 1500자 이상)")
            return False
        
        if text_length > 1800:
            logger.warning(f"본문 글자수 초과: {text_length}자 (요구: 1800자 이하)")
            return False
        
        logger.debug(f"본문 검증 통과: {text_length}자")
        return True


def generate_image(keyword: str, title: str = "") -> Optional[str]:
    """
    DALL-E를 사용하여 이미지를 생성합니다. (옵션)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        
    Returns:
        생성된 이미지 URL 또는 None
    """
    logger.info(f"이미지 생성 시작: {keyword}")
    # TODO: DALL-E API 호출 구현
    pass



