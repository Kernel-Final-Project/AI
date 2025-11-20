"""
본문 생성 모듈
AI2 담당
"""
import time
from typing import Dict, Optional
from content_ai.gpt_utils import call_gpt
from content_ai.prompt_builder import load_prompt, format_outline_for_prompt
from utils.logger import logger


def generate_content_text(
    keyword: str,
    title: str,
    outline: Dict,
    product_info: str = "",
    max_retries: int = 2
) -> Optional[str]:
    """
    GPT로 본문 텍스트 생성 (재시도 로직 포함)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인 (딕셔너리)
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 2)
        
    Returns:
        생성된 본문 텍스트 (실패 시 None)
    """
    logger.info(f"본문 생성 시작: {keyword} - {title}")
    
    for attempt in range(max_retries):
        try:
            # 프롬프트 로드 및 아웃라인 포맷팅
            system_prompt = load_prompt("content_prompt")
            outline_str = format_outline_for_prompt(outline) if isinstance(outline, dict) else str(outline)
            
            user_prompt = f"""키워드: {keyword}
제목: {title}
아웃라인:
{outline_str}
상품 정보: {product_info if product_info else "없음"}"""
            
            # GPT 호출
            response = call_gpt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=2
            )
            
            if not response:
                logger.warning(f"GPT 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            
            # 본문 검증 (2600자 이하로 완화)
            content_length = len(response)
            if content_length <= 2600:
                logger.info(f"본문 생성 완료: {content_length}자 (요약 후처리 필요)")
                return response
            else:
                logger.warning(f"본문 길이가 기준 초과: {content_length}자 (요구: 2600자 이하). 재시도 ({attempt+1}/{max_retries})")
            
            # 재시도 전 대기
            if attempt < max_retries - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"본문 생성 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"본문 생성 실패: 최대 재시도 횟수({max_retries}) 초과")
    return None


def summarize_content(content: str, max_retries: int = 2) -> Optional[str]:
    """
    생성된 본문을 2100~2300자로 요약
    
    Args:
        content: 원본 본문 (2600자 이하)
        max_retries: 최대 재시도 횟수 (기본값: 2)
        
    Returns:
        요약된 본문 (2100~2300자) 또는 None
    """
    logger.info(f"본문 요약 시작: {len(content)}자 → 2100~2300자")
    
    for attempt in range(max_retries):
        try:
            # 프롬프트 로드
            system_prompt = load_prompt("summarize_prompt")
            user_prompt = f"원본 본문:\n{content}"
            
            # GPT 호출
            response = call_gpt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o-mini",
                temperature=0.5,  # 요약은 낮은 temperature 권장
                max_retries=2
            )
            
            if not response:
                logger.warning(f"GPT 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            
            # 요약본 검증 (2100~2300자)
            summary_length = len(response)
            if 2100 <= summary_length <= 2300:
                logger.info(f"본문 요약 완료: {summary_length}자")
                return response
            elif 2050 <= summary_length < 2100:
                logger.warning(f"요약본 길이가 최소 기준 미달: {summary_length}자 (요구: 2100~2300자). 재시도 ({attempt+1}/{max_retries})")
            elif 2300 < summary_length <= 2350:
                logger.warning(f"요약본 길이가 최대 기준 초과: {summary_length}자 (요구: 2100~2300자). 재시도 ({attempt+1}/{max_retries})")
            else:
                logger.warning(f"요약본 길이가 범위를 벗어남: {summary_length}자 (요구: 2100~2300자). 재시도 ({attempt+1}/{max_retries})")
            
            # 재시도 전 대기
            if attempt < max_retries - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"본문 요약 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"본문 요약 실패: 최대 재시도 횟수({max_retries}) 초과")
    return None


def validate_content(content: str) -> bool:
    """
    생성된 본문 검증
    
    Args:
        content: 생성된 본문 텍스트
        
    Returns:
        검증 통과 여부
    """
    if not content:
        logger.warning("본문이 비어있습니다.")
        return False
    
    content_length = len(content)
    
    # 1. 글자수 검증 (2100~2300자)
    if content_length < 2100 or content_length > 2300:
        logger.warning(f"본문 길이가 올바르지 않습니다. (현재: {content_length}자, 요구: 2100~2300자)")
        return False
    
    # 2. h2 태그 확인
    if "<h2>" not in content and "<h2 " not in content:
        logger.warning("본문에 h2 태그가 없습니다.")
        return False
    
    # 3. h3 태그 확인 (선택적)
    # h3는 있을 수도 없을 수도 있으므로 경고만
    
    logger.info(f"본문 검증 통과: {content_length}자")
    return True


def create_fallback_content(keyword: str, title: str, outline: Dict) -> str:
    """
    모든 시도 실패 시 기본 본문 생성 (폴백 메커니즘)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인 (딕셔너리)
        
    Returns:
        기본 본문 텍스트
    """
    fallback_content = f"<h2>{title}</h2>\n<p>{keyword}에 대한 정보를 제공합니다.</p>\n"
    
    if outline and "h2" in outline:
        for h2_item in outline["h2"]:
            h2_title = h2_item.get("title", "")
            fallback_content += f"<h2>{h2_title}</h2>\n<p>{h2_title}에 대한 내용입니다.</p>\n"
            
            h3_list = h2_item.get("h3", [])
            for h3_title in h3_list:
                fallback_content += f"<h3>{h3_title}</h3>\n<p>{h3_title}에 대한 설명입니다.</p>\n"
    
    logger.warning(f"폴백 본문 생성: {len(fallback_content)}자")
    return fallback_content


def generate_content(
    keyword: str,
    title: str,
    outline: Dict,
    product_info: str = "",
    max_retries: int = 2
) -> str:
    """
    본문 생성 통합 함수 (전체 프로세스 재시도 포함)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인 (딕셔너리)
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 2)
        
    Returns:
        생성된 본문 텍스트 (실패 시 폴백 본문)
    """
    for attempt in range(max_retries):
        try:
            # 1. 본문 생성 (2600자 이하)
            content = generate_content_text(keyword, title, outline, product_info, max_retries=2)
            
            if not content:
                logger.warning(f"본문 생성 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
            
            # 2. 조건부 요약 후처리
            content_length = len(content)
            if content_length > 1800:
                # 원본이 1800자 초과면 요약 후처리 진행 (2100~2300자)
                logger.info(f"원본 본문이 1800자 초과({content_length}자)이므로 요약 후처리 진행")
                summarized = summarize_content(content, max_retries=2)
                
                if not summarized:
                    logger.warning(f"본문 요약 실패. 재시도 ({attempt+1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    continue
                
                final_content = summarized
            else:
                # 원본이 1800자 이하면 그대로 사용
                logger.info(f"원본 본문이 1800자 이하({content_length}자)이므로 요약 후처리 건너뜀")
                final_content = content
            
            # 3. 최종 검증
            if validate_content(final_content):
                logger.info(f"본문 생성 성공: {len(final_content)}자")
                return final_content
            else:
                logger.warning(f"본문 검증 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
                
        except Exception as e:
            logger.error(f"본문 생성 프로세스 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    # 모든 재시도 실패 시 폴백 본문 반환
    logger.error(f"본문 생성 최종 실패: 최대 재시도 횟수({max_retries}) 초과. 폴백 본문 사용")
    return create_fallback_content(keyword, title, outline)
