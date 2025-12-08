"""
제목 생성 모듈
AI2 담당
"""
import re
import time
from typing import List, Optional
from content_ai.gpt_utils import generate_with_prompt
from utils.logger import logger


def generate_titles(keyword: str, product_info: str = "", max_retries: int = 3) -> List[str]:
    """
    GPT로 제목 리스트 생성 (재시도 로직 포함)
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 제목 리스트 (최소 2개 이상)
    """
    logger.info(f"제목 생성 시작: {keyword}")
    
    for attempt in range(max_retries):
        try:
            # GPT 호출
            response = generate_with_prompt(
                prompt_name="title_prompt",
                user_data={
                    "키워드": keyword,
                    "상품 정보": product_info if product_info else "없음"
                },
                temperature=0.8,  # 다양성을 위해 조금 높게
                max_retries=3
            )
            
            if not response:
                logger.warning(f"GPT 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 1초 대기 후 재시도
                continue
            
            # GPT 원본 응답 로그
            logger.debug(f"GPT 원본 응답 (시도 {attempt+1}):\n{response[:500]}...")
            
            # bullet 형태로 파싱
            titles = parse_titles_from_response(response)
            logger.info(f"파싱된 제목 {len(titles)}개: {titles}")
            
            # 제목이 2개 이상이고, 최소 1개는 유효한지 검증
            if len(titles) >= 2:
                # 유효한 제목 체크 (키워드 포함, 키워드 제외 나머지 텍스트 길이 제한)
                # 키워드 제외 나머지 텍스트는 최대 25자까지 허용
                valid_titles = []
                for t in titles:
                    if keyword in t:
                        # 키워드를 제외한 나머지 텍스트 길이 계산
                        remaining_text = t.replace(keyword, "").strip()
                        remaining_length = len(remaining_text)
                        # 키워드 제외 나머지가 25자 이하이고, 전체 길이는 40자 이하
                        if remaining_length <= 25 and len(t) <= 40:
                            valid_titles.append(t)
                        else:
                            logger.debug(f"제목 길이 초과: '{t}' (전체: {len(t)}자, 키워드 제외: {remaining_length}자)")
                    else:
                        logger.debug(f"키워드 미포함: '{t}'")
                
                # 무효한 제목도 로그에 기록
                invalid_titles = [
                    t for t in titles 
                    if t not in valid_titles
                ]
                
                if invalid_titles:
                    logger.debug(f"무효한 제목 {len(invalid_titles)}개: {invalid_titles}")
                
                if valid_titles:
                    logger.info(f"제목 {len(titles)}개 생성 완료 (유효: {len(valid_titles)}개)")
                    logger.info(f"유효한 제목 목록: {valid_titles}")
                    return titles
                else:
                    logger.warning(f"제목 {len(titles)}개 생성되었으나 유효한 제목 없음")
                    logger.warning(f"생성된 제목 목록: {titles}")
                    logger.warning(f"재시도 ({attempt+1}/{max_retries})")
            else:
                logger.warning(f"제목 {len(titles)}개만 생성됨 (최소 2개 필요)")
                logger.warning(f"생성된 제목 목록: {titles}")
                logger.warning(f"재시도 ({attempt+1}/{max_retries})")
            
            # 재시도 전 대기
            if attempt < max_retries - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"제목 생성 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"제목 생성 실패: 최대 재시도 횟수({max_retries}) 초과")
    return []


def parse_titles_from_response(response: str) -> List[str]:
    """
    GPT 응답에서 제목 리스트 추출
    
    Args:
        response: GPT 응답 텍스트
        
    Returns:
        제목 리스트
    """
    titles = []
    lines = response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 빈 줄 스킵
        if not line:
            continue
        
        # bullet 제거 (-, •, *, 숫자 등)
        line = re.sub(r'^[-•*]\s*', '', line)  # -, •, * 제거
        line = re.sub(r'^\d+[.)]\s*', '', line)  # 1., 2) 등 제거
        line = re.sub(r'^[가-힣]+[.)]\s*', '', line)  # 가), 나) 등 제거
        
        # 최소 길이 체크 (10자 이상)
        if len(line) >= 10:
            titles.append(line)
    
    # 최대 5개만 반환
    return titles[:5]


def select_best_title(titles: List[str], keyword: str) -> str:
    """
    생성된 제목 중 최적 제목 선택
    
    Args:
        titles: 생성된 제목 리스트
        keyword: 원본 키워드
        
    Returns:
        선택된 최적 제목
    """
    if not titles:
        logger.warning("선택할 제목이 없습니다.")
        return ""
    
    # 금지어 리스트
    forbidden_words = [
        "대박", "역대급", "초특가", "완판", "폭발적", 
        "지금 구매", "한정", "서둘러", "파격", "할인", "쿠폰",
        "에 대해 알아보자", "완벽 가이드", "모든 것", 
        "정리해드립니다", "살펴보기"
    ]
    
    scored_titles = []
    
    for title in titles:
        score = 0
        
        # 1. 길이 검증 (키워드 제외 나머지 텍스트 기준)
        keyword_pos = title.find(keyword)
        if keyword_pos != -1:
            # 키워드를 제외한 나머지 텍스트 길이
            remaining_text = title.replace(keyword, "").strip()
            remaining_len = len(remaining_text)
            
            # 키워드 제외 나머지가 15-20자면 최적
            if 15 <= remaining_len <= 20:
                score += 10
            elif 10 <= remaining_len < 15 or 20 < remaining_len <= 25:
                score += 5
            elif remaining_len > 25:
                score -= 10  # 25자 초과는 큰 감점
            elif remaining_len < 10:
                score -= 5  # 너무 짧으면 감점
        else:
            # 키워드가 없으면 전체 길이로 평가
            title_len = len(title)
            if 30 <= title_len <= 33:
                score += 10
            elif 25 <= title_len < 30 or 33 < title_len <= 35:
                score += 5
            elif title_len > 35:
                score -= 10
        
        # 2. 키워드 포함 여부 (앞 10자 이내가 최적)
        if keyword_pos != -1:
            if keyword_pos <= 10:
                score += 10  # 앞 10자 이내
            else:
                score += 5  # 다른 위치
        else:
            score -= 20  # 키워드 미포함은 큰 감점
        
        # 3. 금지어 검사
        has_forbidden = any(word in title for word in forbidden_words)
        if has_forbidden:
            score -= 50  # 큰 감점
        
        # 4. 숫자 포함 (권장)
        if re.search(r'\d', title):
            score += 5
        
        # 5. 질문형 (권장)
        if '?' in title or '왜' in title or '어떻게' in title or '무엇' in title:
            score += 3
        
        # 6. 같은 뜻의 표현 중복 체크 (인기+핫, 추천+BEST 등)
        if ('인기' in title and '핫' in title) or \
           ('추천' in title and 'BEST' in title) or \
           ('추천' in title and 'best' in title):
            score -= 5
        
        # 7. 키워드 중복 체크 (동일 키워드 2회 이상 사용 금지)
        keyword_count = title.count(keyword)
        if keyword_count >= 2:
            score -= 10
        
        scored_titles.append((title, score))
    
    # 점수 순으로 정렬
    scored_titles.sort(key=lambda x: x[1], reverse=True)
    
    best_title = scored_titles[0][0]
    best_score = scored_titles[0][1]
    
    logger.info(f"최적 제목 선택: {best_title} (점수: {best_score}, 길이: {len(best_title)}자)")
    
    # 모든 제목의 점수 상세 로그 출력
    logger.info(f"제목 점수 평가 결과 (총 {len(scored_titles)}개):")
    for i, (title, score) in enumerate(scored_titles, 1):
        title_len = len(title)
        keyword_included = keyword in title
        keyword_pos = title.find(keyword) if keyword_included else -1
        logger.info(f"  {i}. [{score}점] {title} (길이: {title_len}자, 키워드 위치: {keyword_pos if keyword_pos >= 0 else '없음'})")
    
    return best_title


def create_fallback_title(keyword: str, product_info: str = "") -> str:
    """
    모든 시도 실패 시 기본 제목 생성 (폴백 메커니즘)
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        
    Returns:
        기본 제목
    """
    # 간단한 템플릿 기반 제목 생성
    templates = [
        f"{keyword} 추천 가이드",
        f"{keyword} 완벽 정리",
        f"{keyword} 알아보기",
        f"{keyword} 선택 가이드"
    ]
    
    # 키워드 길이에 따라 템플릿 선택
    if len(keyword) <= 5:
        fallback_title = templates[0]  # "요가매트 추천 가이드"
    elif len(keyword) <= 10:
        fallback_title = templates[1]  # "프리미엄 요가매트 완벽 정리"
    else:
        fallback_title = templates[2]  # "프리미엄 요가매트 알아보기"
    
    logger.warning(f"폴백 제목 생성: {fallback_title}")
    return fallback_title


def generate_title(keyword: str, product_info: str = "", max_retries: int = 3) -> Optional[str]:
    """
    제목 생성 통합 함수 (전체 프로세스 재시도 포함)
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 최적 제목 (실패 시 폴백 제목)
    """
    for attempt in range(max_retries):
        try:
            # 1. 제목 리스트 생성
            titles = generate_titles(keyword, product_info, max_retries=3)
            
            if not titles:
                logger.warning(f"제목 리스트 생성 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 2초 대기 후 재시도
                continue
            
            logger.info(f"제목 리스트 생성 성공: {len(titles)}개 제목")
            
            # 2. 최적 제목 선택
            logger.info("최적 제목 선택 시작...")
            best_title = select_best_title(titles, keyword)
            
            if not best_title:
                logger.warning(f"최적 제목 선택 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
            
            # 3. 선택된 제목의 품질 검증
            # 키워드 포함 여부와 키워드 제외 나머지 텍스트 길이 체크
            if keyword in best_title:
                remaining_text = best_title.replace(keyword, "").strip()
                remaining_length = len(remaining_text)
                if remaining_length <= 25 and len(best_title) <= 40:
                    logger.info(f"제목 생성 성공: {best_title}")
                    logger.info(f"제목 상세: 전체 {len(best_title)}자, 키워드 제외 {remaining_length}자")
                    return best_title
                else:
                    logger.warning(f"선택된 제목이 품질 기준 미달 (전체: {len(best_title)}자, 키워드 제외: {remaining_length}자). 재시도 ({attempt+1}/{max_retries})")
            else:
                logger.warning(f"선택된 제목에 키워드 미포함. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
                
        except Exception as e:
            logger.error(f"제목 생성 프로세스 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    # 모든 재시도 실패 시 폴백 제목 반환
    logger.error(f"제목 생성 최종 실패: 최대 재시도 횟수({max_retries}) 초과. 폴백 제목 사용")
    return create_fallback_title(keyword, product_info)

