"""
싸다구 상품 정보 추출 모듈
"""
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urljoin, urlparse

from utils.logger import logger
from parsers.ssadagu.config import SSADAGU_SELECTORS, BASE_URL


def extract_price(price_element: Tag) -> Optional[str]:
    """
    가격 정보 추출 (예: "4,191원")
    
    Args:
        price_element: 가격이 포함된 Tag 요소
        
    Returns:
        가격 문자열 (예: "4,191원") 또는 None
    """
    if not price_element:
        return None
    
    # 텍스트 추출
    price_text = price_element.get_text(strip=True)
    
    # 숫자와 "원" 추출
    # 예: "4,191원 " -> "4,191원"
    price_match = re.search(r'[\d,]+', price_text)
    if price_match:
        price_num = price_match.group()
        # "원"이 있으면 추가
        if '원' in price_text:
            return f"{price_num}원"
        return price_num
    
    return None


def extract_image_url(img_element: Tag) -> Optional[str]:
    """
    이미지 URL 추출 (lazy loading 대응)
    
    Args:
        img_element: img Tag 요소
        
    Returns:
        이미지 URL 또는 None
    """
    if not img_element:
        return None
    
    # src 우선, 없으면 data-src
    image_url = img_element.get('src') or img_element.get('data-src')
    
    if not image_url:
        return None
    
    # 상대 경로를 절대 경로로 변환
    if image_url.startswith('//'):
        return f"https:{image_url}"
    elif image_url.startswith('/'):
        return urljoin(BASE_URL, image_url)
    elif not image_url.startswith('http'):
        return urljoin(BASE_URL, image_url)
    
    return image_url


def extract_product_id(product_url: str) -> Optional[str]:
    """
    상품 URL에서 num_iid 추출
    
    Args:
        product_url: 상품 상세 페이지 URL
        
    Returns:
        num_iid 또는 None
    """
    match = re.search(r'num_iid=(\d+)', product_url)
    if match:
        return match.group(1)
    return None


def extract_product_info(product_element: Tag) -> Optional[Dict[str, str]]:
    """
    하나의 상품 요소에서 정보 추출
    
    Args:
        product_element: 상품 정보를 담고 있는 div.product_info Tag
        
    Returns:
        상품 정보 딕셔너리 또는 None
    """
    try:
        # 상품명
        title_elem = product_element.select_one(SSADAGU_SELECTORS["product_title"])
        if not title_elem:
            logger.warning("상품명을 찾을 수 없습니다")
            return None
        
        title = title_elem.get_text(strip=True)
        
        # 가격
        price_elem = product_element.select_one(SSADAGU_SELECTORS["product_price"])
        price = extract_price(price_elem) if price_elem else None
        
        # 이미지 (여러 방법 시도)
        img_elem = None
        
        # 방법 1: product-image-container 내부에서 찾기
        image_container = product_element.select_one(SSADAGU_SELECTORS.get("product_image_container", "div.product-image-container"))
        if image_container:
            img_elem = image_container.select_one("img.hover-big")
        
        # 방법 2: 직접 선택자로 찾기
        if not img_elem:
            img_elem = product_element.select_one(SSADAGU_SELECTORS["product_image"])
        
        # 방법 3: 형제 요소에서 찾기 (product_info와 product-image-container가 형제일 경우)
        if not img_elem:
            # 부모 요소에서 product-image-container 찾기
            parent = product_element.parent
            if parent:
                image_container = parent.select_one("div.product-image-container")
                if image_container:
                    img_elem = image_container.select_one("img.hover-big")
        
        image_url = extract_image_url(img_elem) if img_elem else None
        
        # 상품 링크
        link_elem = product_element.select_one(SSADAGU_SELECTORS["product_link"])
        if not link_elem:
            logger.warning("상품 링크를 찾을 수 없습니다")
            return None
        
        product_url = link_elem.get('href', '')
        # 상대 경로를 절대 경로로 변환
        if product_url and not product_url.startswith('http'):
            product_url = urljoin(BASE_URL, product_url)
        
        # 상품 ID 추출
        product_id = extract_product_id(product_url)
        
        return {
            "title": title,
            "price": price or "",
            "image_url": image_url or "",
            "product_url": product_url,
            "product_id": product_id or "",
        }
        
    except Exception as e:
        logger.error(f"상품 정보 추출 중 오류: {e}")
        return None


def extract_products_from_html(html: str) -> List[Dict[str, str]]:
    """
    HTML에서 모든 상품 정보 추출
    
    Args:
        html: HTML 문자열
        
    Returns:
        상품 정보 리스트
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 상품 리스트 컨테이너 찾기
    product_elements = soup.select(SSADAGU_SELECTORS["product_list"])
    
    if not product_elements:
        logger.warning("상품 요소를 찾을 수 없습니다")
        return []
    
    logger.info(f"상품 요소 {len(product_elements)}개 발견")
    
    products = []
    for elem in product_elements:
        product_info = extract_product_info(elem)
        if product_info:
            products.append(product_info)
    
    logger.info(f"상품 정보 추출 완료: {len(products)}개")
    return products

