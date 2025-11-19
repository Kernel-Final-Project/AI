"""
Google Trends 기반 이슈 상품 50개 수집 모듈
AI1 담당
"""
from typing import List, Dict
from utils.logger import logger


def collect_trends(count: int = 50) -> List[Dict]:
    """
    Google Trends에서 이슈 상품 키워드를 수집합니다.
    
    Args:
        count: 수집할 키워드 개수 (기본값: 50)
        
    Returns:
        트렌드 키워드 리스트
        예: [{"keyword": "아이패드", "score": 95, "related": [...]}, ...]
    """
    logger.info(f"Google Trends에서 {count}개 키워드 수집 시작")
    # TODO: 구현 필요
    pass


def expand_related_keywords(keyword: str) -> List[str]:
    """
    키워드의 관련 검색어 및 주제를 확장합니다.
    
    Args:
        keyword: 기준 키워드
        
    Returns:
        관련 키워드 리스트
    """
    logger.info(f"'{keyword}' 관련 키워드 확장")
    # TODO: 구현 필요
    pass


def filter_keywords(keywords: List[Dict]) -> List[Dict]:
    """
    불필요한 키워드를 필터링합니다.
    (연예/정치/뉴스 등 제외)
    
    Args:
        keywords: 필터링할 키워드 리스트
        
    Returns:
        필터링된 키워드 리스트
    """
    logger.info(f"{len(keywords)}개 키워드 필터링 시작")
    # TODO: 구현 필요
    pass

