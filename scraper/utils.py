"""
크롤링 유틸리티 함수들
"""
from typing import Optional
from bs4 import BeautifulSoup
from utils.logger import logger


def clean_html(html: str) -> str:
    """
    HTML을 정리합니다 (불필요한 공백, 주석 제거 등).
    
    Args:
        html: 원본 HTML
        
    Returns:
        정리된 HTML
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 주석 제거
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    return str(soup)


def extract_text(html: str, selector: Optional[str] = None) -> str:
    """
    HTML에서 텍스트를 추출합니다.
    
    Args:
        html: HTML 문자열
        selector: CSS 선택자 (None이면 전체 텍스트)
        
    Returns:
        추출된 텍스트
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    if selector:
        elements = soup.select(selector)
        texts = [elem.get_text(strip=True) for elem in elements]
        return '\n'.join(texts)
    else:
        return soup.get_text(strip=True)


