"""
무신사 상품 정보 추출 모듈
"""
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urljoin

from utils.logger import logger
from parsers.musinsa.config import MUSINSA_SELECTORS, BASE_URL


def extract_price(price_element: Tag) -> Optional[str]:
    """
    가격 정보 추출 (예: "89,680원")
    
    Args:
        price_element: 가격이 포함된 Tag 요소
        
    Returns:
        가격 문자열 (예: "89,680원") 또는 None
    """
    if not price_element:
        return None
    
    # 텍스트 추출
    price_text = price_element.get_text(strip=True)
    
    # 숫자와 "원" 추출
    # 예: "89,680원" -> "89,680원"
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
    상품 URL에서 상품 ID 추출
    예: https://www.musinsa.com/products/5757332 -> 5757332
    
    Args:
        product_url: 상품 상세 페이지 URL
        
    Returns:
        상품 ID 또는 None
    """
    match = re.search(r'/products/(\d+)', product_url)
    if match:
        return match.group(1)
    return None


def extract_product_info(product_element: Tag) -> Optional[Dict[str, str]]:
    """
    하나의 상품 요소에서 정보 추출
    
    Args:
        product_element: 상품 정보를 담고 있는 div.sc-hdBJTi.gAWtWT Tag
        
    Returns:
        상품 정보 딕셔너리 또는 None
    """
    try:
        # 상품명
        title_elem = product_element.select_one(MUSINSA_SELECTORS["product_title"])
        if not title_elem:
            logger.warning("상품명을 찾을 수 없습니다")
            return None
        
        title = title_elem.get_text(strip=True)
        
        # 가격 컨테이너 찾기 (할인율 + 가격이 포함된 div)
        price_container = product_element.select_one(MUSINSA_SELECTORS["product_price"])
        if not price_container:
            logger.warning("가격 컨테이너를 찾을 수 없습니다")
            return None
        
        # 할인율 span 제외하고 가격 span 찾기
        # text-red 클래스가 있는 span은 할인율이므로 제외
        price_span = None
        
        # 가격 컨테이너 내의 모든 span 찾기
        all_spans = price_container.select("span")
        
        # 방법 1: text-red가 없는 span 중에서 "원"이 포함된 것 찾기
        for span in all_spans:
            span_classes = span.get('class', [])
            span_text = span.get_text(strip=True)
            
            # text-red 클래스가 없고 "원"이 포함된 span이 가격
            if 'text-red' not in ' '.join(span_classes) and '원' in span_text:
                price_span = span
                break
        
        # 방법 2: 방법 1이 실패하면 모든 span에서 "원"이 포함되고 "%"가 없는 것 찾기
        if not price_span:
            for span in all_spans:
                span_text = span.get_text(strip=True)
                if '원' in span_text and '%' not in span_text:
                    price_span = span
                    break
        
        if price_span:
            # 가격 span에서 숫자 추출
            price_text = price_span.get_text(strip=True)
            price_match = re.search(r'([\d,]+)\s*원', price_text)
            if price_match:
                price_num = price_match.group(1)
                price = f"{price_num}원"
            else:
                price = price_text
        else:
            # span을 찾지 못한 경우 전체 텍스트에서 "원"이 포함된 숫자 찾기
            price_text = price_container.get_text(strip=True)
            price_match = re.search(r'([\d,]+)\s*원', price_text)
            if price_match:
                price_num = price_match.group(1)
                price = f"{price_num}원"
            else:
                # 마지막 fallback
                price = extract_price(price_container)
        
        # 이미지
        img_elem = product_element.select_one(MUSINSA_SELECTORS["product_image"])
        image_url = extract_image_url(img_elem) if img_elem else None
        
        # 상품 링크 및 ID 찾기 (여러 방법 시도)
        link_elem = None
        product_url = None
        product_id = None
        
        # 먼저 data-item-id로 상품 ID 추출 시도 (가장 확실한 방법)
        product_id_elem = product_element.select_one("[data-item-id]")
        if product_id_elem:
            product_id = product_id_elem.get('data-item-id')
        
        # 방법 1: gtm-select-item 클래스로 찾기
        link_elem = product_element.select_one(MUSINSA_SELECTORS["product_link"])
        
        # 방법 2: data-item-id 속성이 있는 링크 찾기
        if not link_elem:
            link_elem = product_element.select_one("a[data-item-id]")
        
        # 방법 3: gtm-view-item-list 클래스로 찾기
        if not link_elem:
            link_elem = product_element.select_one("a.gtm-view-item-list")
        
        # 방법 4: href에 /products/가 포함된 링크 찾기
        if not link_elem:
            all_links = product_element.select("a")
            for link in all_links:
                href = link.get('href', '')
                if '/products/' in href:
                    link_elem = link
                    break
        
        if link_elem:
            # href 속성에서 URL 추출
            product_url = link_elem.get('href', '')
            
            # data-item-id에서 상품 ID 추출 (아직 없으면)
            if not product_id:
                product_id = link_elem.get('data-item-id')
            
            # 상대 경로를 절대 경로로 변환
            if product_url and not product_url.startswith('http'):
                product_url = urljoin(BASE_URL, product_url)
        
        # 링크를 찾지 못했지만 product_id가 있으면 URL 생성
        if not product_url and product_id:
            product_url = f"https://www.musinsa.com/products/{product_id}"
        
        # 상품 ID 추출 (URL에서, 아직 없으면)
        if not product_id and product_url:
            product_id = extract_product_id(product_url)
        
        # 최종적으로 URL이 없으면 상품 ID로 생성
        if not product_url:
            if product_id:
                product_url = f"https://www.musinsa.com/products/{product_id}"
            else:
                logger.warning("상품 링크와 ID를 모두 찾을 수 없습니다")
                return None
        
        # 상품 ID가 있지만 URL이 없으면 URL 생성 (최종 안전장치)
        if product_id and not product_url:
            product_url = f"https://www.musinsa.com/products/{product_id}"
        
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
    product_list_container = soup.select_one(MUSINSA_SELECTORS["product_list"])
    
    if not product_list_container:
        logger.warning("상품 리스트 컨테이너를 찾을 수 없습니다")
        return []
    
    # 개별 상품 요소 찾기
    product_elements = product_list_container.select(MUSINSA_SELECTORS["product_item"])
    
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


