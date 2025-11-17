"""
트렌드 상품 1개 랜덤 선택 모듈
AI1 담당
"""
import random
from typing import Dict, List
from utils.logger import logger


def select_random_keyword(keywords: List[Dict]) -> Dict:
    """
    수집된 키워드 중 1개를 랜덤으로 선택합니다.
    
    Args:
        keywords: 선택할 키워드 리스트
        
    Returns:
        선택된 키워드 딕셔너리
        예: {"keyword": "아이패드", "score": 95, ...}
    """
    if not keywords:
        logger.warning("선택할 키워드가 없습니다.")
        return None
    
    selected = random.choice(keywords)
    logger.info(f"선택된 키워드: {selected.get('keyword', 'Unknown')}")
    return selected


def rank_keywords_by_score(keywords: List[Dict]) -> List[Dict]:
    """
    키워드를 점수 기반으로 정렬합니다.
    
    Args:
        keywords: 정렬할 키워드 리스트
        
    Returns:
        점수 내림차순으로 정렬된 키워드 리스트
    """
    logger.info(f"{len(keywords)}개 키워드 점수 기반 정렬")
    sorted_keywords = sorted(keywords, key=lambda x: x.get('score', 0), reverse=True)
    return sorted_keywords

