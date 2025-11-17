"""
ssadagu.kr 쇼핑몰 상품 정보 크롤링 모듈
AI1 담당
"""
from typing import List, Dict
from utils.logger import logger


def search_products(keyword: str) -> List[Dict]:
    """
    ssadagu.kr에서 키워드로 상품을 검색하고 정보를 수집합니다.
    
    Args:
        keyword: 검색 키워드
        
    Returns:
        상품 정보 리스트
        예: [{"title": "상품명", "price": "가격", "url": "...", ...}, ...]
    """
    logger.info(f"ssadagu.kr에서 '{keyword}' 검색 시작")
    # TODO: 구현 필요
    pass


def extract_product_titles(products: List[Dict]) -> List[str]:
    """
    상품 정보에서 제목만 추출합니다.
    
    Args:
        products: 상품 정보 리스트
        
    Returns:
        상품 제목 리스트
    """
    logger.info(f"{len(products)}개 상품 제목 추출")
    titles = [product.get('title', '') for product in products]
    return titles


def format_product_data_for_llm(products: List[Dict]) -> str:
    """
    LLM 입력용으로 상품 데이터를 텍스트 형식으로 변환합니다.
    
    Args:
        products: 상품 정보 리스트
        
    Returns:
        포맷팅된 텍스트 데이터
    """
    logger.info("상품 데이터 LLM 입력용 포맷팅")
    # TODO: 구현 필요
    pass

