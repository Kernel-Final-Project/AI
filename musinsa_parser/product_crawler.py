"""
상품 크롤링 모듈
XPath 기반
"""
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from musinsa_parser.config import BASE_URL, MUSINSA_XPATHS, SCROLL_PAUSE_TIME, MAX_SCROLL_ATTEMPTS
from musinsa_parser.category_crawler import navigate_to_category


def scroll_to_load_more(driver: webdriver.Chrome) -> bool:
    """
    무한 스크롤 처리
    
    Args:
        driver: Selenium WebDriver
        
    Returns:
        더 로드할 상품이 있는지 여부
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE_TIME)
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != last_height


def extract_products_from_html(html: str) -> List[Dict[str, str]]:
    """
    HTML에서 상품 정보 추출 (BeautifulSoup 사용)
    
    Args:
        html: HTML 문자열
        
    Returns:
        상품 정보 리스트
    """
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    
    # 상품 리스트 컨테이너 찾기
    product_list = soup.select_one("div[class*='GoodsList__List']")
    if not product_list:
        logger.warning("상품 리스트 컨테이너를 찾을 수 없습니다")
        return []
    
    # 개별 상품 요소 찾기
    product_elements = product_list.select("div[class*='sc-hdBJTi']")
    
    if not product_elements:
        logger.warning("상품 요소를 찾을 수 없습니다")
        return []
    
    logger.info(f"상품 요소 {len(product_elements)}개 발견")
    
    for elem in product_elements:
        try:
            # 상품명
            title_elem = elem.select_one("a.gtm-select-item span")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            
            # 상품 ID (data-item-id)
            link_elem = elem.select_one("a[data-item-id]")
            product_id = None
            product_url = None
            
            if link_elem:
                product_id = link_elem.get('data-item-id')
                product_url = link_elem.get('href')
                if product_url and not product_url.startswith('http'):
                    product_url = f"https://www.musinsa.com{product_url}"
            
            # URL이 없으면 ID로 생성
            if not product_url and product_id:
                product_url = f"https://www.musinsa.com/products/{product_id}"
            
            # 가격
            price_container = elem.select_one("div[class*='sc-jwTyAe']")
            price = None
            if price_container:
                # text-red가 없는 span 중에서 "원"이 포함된 것 찾기
                all_spans = price_container.select("span")
                for span in all_spans:
                    span_classes = span.get('class', [])
                    span_text = span.get_text(strip=True)
                    if 'text-red' not in ' '.join(span_classes) and '원' in span_text and '%' not in span_text:
                        import re
                        price_match = re.search(r'([\d,]+)\s*원', span_text)
                        if price_match:
                            price = f"{price_match.group(1)}원"
                        break
            
            # 이미지
            img_elem = elem.select_one("img[data-mds='Image']")
            image_url = img_elem.get('src') if img_elem else None
            
            if title and product_id:
                products.append({
                    "title": title,
                    "price": price or "N/A",
                    "product_id": product_id,
                    "product_url": product_url or "N/A",
                    "image_url": image_url or "N/A"
                })
        except Exception as e:
            logger.debug(f"상품 정보 추출 실패: {e}")
            continue
    
    return products


def crawl_category_page(driver: webdriver.Chrome, category_url: str, max_products: int = 100) -> List[Dict[str, str]]:
    """
    카테고리 페이지에서 상품 크롤링
    
    Args:
        driver: Selenium WebDriver
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수
        
    Returns:
        상품 정보 리스트
    """
    try:
        logger.info(f"카테고리 페이지 크롤링 시작: {category_url}")
        
        driver.get(category_url)
        time.sleep(2)
        
        all_products = []
        scroll_attempts = 0
        
        while len(all_products) < max_products and scroll_attempts < MAX_SCROLL_ATTEMPTS:
            html = driver.page_source
            products = extract_products_from_html(html)
            
            # 중복 제거
            existing_ids = {p.get("product_id") for p in all_products if p.get("product_id")}
            new_products = [p for p in products if p.get("product_id") not in existing_ids]
            
            all_products.extend(new_products)
            logger.info(f"현재 수집된 상품: {len(all_products)}개 (목표: {max_products}개)")
            
            if len(all_products) >= max_products:
                break
            
            if not scroll_to_load_more(driver):
                logger.info("더 이상 로드할 상품이 없습니다")
                break
            
            scroll_attempts += 1
        
        result = all_products[:max_products]
        logger.info(f"크롤링 완료: {len(result)}개 상품 수집")
        return result
        
    except Exception as e:
        logger.error(f"카테고리 페이지 크롤링 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def crawl_from_main(category_path: List[str], max_products: int = 100) -> List[Dict[str, str]]:
    """
    메인 페이지에서 시작하여 카테고리로 이동 후 크롤링
    
    Args:
        category_path: 카테고리 경로 리스트 (예: ["뷰티", "스킨케어"])
        max_products: 최대 수집할 상품 개수
        
    Returns:
        상품 정보 리스트
    """
    category_path_str = " > ".join(category_path)
    logger.info(f"카테고리 경로 '{category_path_str}' 크롤링 시작")
    
    driver = None
    try:
        driver = setup_browser(headless=False)
        
        category_url = navigate_to_category(driver, category_path)
        if not category_url:
            logger.error("카테고리로 이동 실패")
            return []
        
        return crawl_category_page(driver, category_url, max_products)
        
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")

