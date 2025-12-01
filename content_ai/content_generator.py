"""
본문 생성 모듈
AI2 담당
"""
from typing import Dict, Optional
from utils.logger import logger
from utils.load_env import get_env
from content_ai.prompt_builder import (
    build_title_prompt,
    build_outline_prompt,
    build_body_prompt
)


def generate_title(keyword: str, product_info: str = "") -> str:
    """
    SEO 최적화된 제목을 생성합니다.
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        
    Returns:
        생성된 제목
    """
    logger.info(f"제목 생성 시작: {keyword}")
    prompt = build_title_prompt(keyword, product_info)
    # TODO: OpenAI API 호출 구현
    pass


def generate_outline(keyword: str, title: str, product_info: str = "") -> Dict:
    """
    블로그 글의 아웃라인을 생성합니다.
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        product_info: 상품 정보 텍스트
        
    Returns:
        아웃라인 딕셔너리
    """
    logger.info(f"아웃라인 생성 시작: {title}")
    prompt = build_outline_prompt(keyword, title, product_info)
    # TODO: OpenAI API 호출 구현
    pass


def generate_body(keyword: str, title: str, outline: Dict, product_info: str = "") -> str:
    """
    블로그 본문을 생성합니다.
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인
        product_info: 상품 정보 텍스트
        
    Returns:
        HTML 형식의 본문
    """
    logger.info(f"본문 생성 시작: {title}")
    prompt = build_body_prompt(keyword, title, outline, product_info)
    # TODO: OpenAI API 호출 구현
    pass


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


def generate_full_content(keyword: str, product_info: str = "") -> Dict:
    """
    전체 콘텐츠를 생성합니다. (제목 + 아웃라인 + 본문 + 이미지)
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        
    Returns:
        생성된 전체 콘텐츠 딕셔너리
    """
    logger.info(f"전체 콘텐츠 생성 시작: {keyword}")
    
    # 제목 생성
    title = generate_title(keyword, product_info)
    
    # 아웃라인 생성
    outline = generate_outline(keyword, title, product_info)
    
    # 본문 생성
    body = generate_body(keyword, title, outline, product_info)
    
    # 이미지 생성 (옵션)
    image_url = generate_image(keyword, title)
    
    return {
        "title": title,
        "outline": outline,
        "body": body,
        "image_url": image_url,
        "keyword": keyword
    }

