"""
무신사 상품 URL 추출 원인 분석
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from parsers.musinsa.crawler import navigate_to_category
from parsers.musinsa.config import MUSINSA_SELECTORS

def analyze_url_extraction():
    """상품 URL 추출 실패 원인 분석"""
    driver = None
    try:
        driver = setup_browser(headless=False)
        
        # 뷰티 > 스킨케어 페이지로 이동
        category_path = ["뷰티", "스킨케어"]
        category_url = navigate_to_category(driver, category_path)
        
        if not category_url:
            logger.error("카테고리로 이동 실패")
            return
        
        logger.info(f"페이지 이동 완료: {category_url}")
        time.sleep(2)
        
        # 현재 페이지 HTML 가져오기
        html = driver.page_source
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 상품 리스트 컨테이너 찾기
        product_list = soup.select_one(MUSINSA_SELECTORS["product_list"])
        if not product_list:
            logger.error("상품 리스트 컨테이너를 찾을 수 없습니다")
            return
        
        # 첫 번째 상품 요소 찾기
        product_elements = product_list.select(MUSINSA_SELECTORS["product_item"])
        if not product_elements:
            logger.error("상품 요소를 찾을 수 없습니다")
            return
        
        logger.info(f"상품 요소 {len(product_elements)}개 발견")
        
        # 첫 번째 상품 상세 분석
        first_product = product_elements[0]
        
        logger.info("\n" + "=" * 80)
        logger.info("첫 번째 상품 HTML 구조 분석")
        logger.info("=" * 80)
        
        # 1. 전체 HTML 출력 (일부)
        logger.info("\n[1] 상품 요소 HTML (처음 500자):")
        logger.info(str(first_product)[:500])
        
        # 2. data-item-id 속성 찾기
        logger.info("\n[2] data-item-id 속성 찾기:")
        data_item_id_elem = first_product.select_one("[data-item-id]")
        if data_item_id_elem:
            data_item_id = data_item_id_elem.get('data-item-id')
            logger.info(f"  ✓ 발견: {data_item_id}")
            logger.info(f"  요소 태그: {data_item_id_elem.name}")
            logger.info(f"  요소 클래스: {data_item_id_elem.get('class', [])}")
        else:
            logger.info("  ✗ data-item-id 속성을 찾을 수 없습니다")
        
        # 3. 링크 요소 찾기 (여러 방법)
        logger.info("\n[3] 링크 요소 찾기:")
        
        # 방법 1: gtm-select-item
        link1 = first_product.select_one("a.gtm-select-item")
        logger.info(f"  방법 1 (a.gtm-select-item): {'✓ 발견' if link1 else '✗ 없음'}")
        if link1:
            logger.info(f"    href: {link1.get('href', 'N/A')}")
            logger.info(f"    data-item-id: {link1.get('data-item-id', 'N/A')}")
            logger.info(f"    클래스: {link1.get('class', [])}")
        
        # 방법 2: a[data-item-id]
        link2 = first_product.select_one("a[data-item-id]")
        logger.info(f"  방법 2 (a[data-item-id]): {'✓ 발견' if link2 else '✗ 없음'}")
        if link2:
            logger.info(f"    href: {link2.get('href', 'N/A')}")
            logger.info(f"    data-item-id: {link2.get('data-item-id', 'N/A')}")
        
        # 방법 3: gtm-view-item-list
        link3 = first_product.select_one("a.gtm-view-item-list")
        logger.info(f"  방법 3 (a.gtm-view-item-list): {'✓ 발견' if link3 else '✗ 없음'}")
        if link3:
            logger.info(f"    href: {link3.get('href', 'N/A')}")
            logger.info(f"    data-item-id: {link3.get('data-item-id', 'N/A')}")
        
        # 방법 4: /products/ 포함 링크
        all_links = first_product.select("a")
        products_link = None
        for link in all_links:
            href = link.get('href', '')
            if '/products/' in href:
                products_link = link
                break
        logger.info(f"  방법 4 (href에 /products/ 포함): {'✓ 발견' if products_link else '✗ 없음'}")
        if products_link:
            logger.info(f"    href: {products_link.get('href', 'N/A')}")
            logger.info(f"    data-item-id: {products_link.get('data-item-id', 'N/A')}")
        
        # 4. 모든 링크 요소 확인
        logger.info("\n[4] 상품 요소 내 모든 링크:")
        for i, link in enumerate(all_links[:5], 1):
            href = link.get('href', '')
            classes = link.get('class', [])
            data_id = link.get('data-item-id', 'N/A')
            logger.info(f"  링크 {i}:")
            logger.info(f"    href: {href[:80] if href else 'N/A'}")
            logger.info(f"    클래스: {classes}")
            logger.info(f"    data-item-id: {data_id}")
        
        # 5. 실제 extract_product_info 함수 테스트
        logger.info("\n[5] extract_product_info 함수 테스트:")
        from parsers.musinsa.product_extractor import extract_product_info
        product_info = extract_product_info(first_product)
        if product_info:
            logger.info(f"  ✓ 추출 성공:")
            logger.info(f"    title: {product_info.get('title', 'N/A')}")
            logger.info(f"    price: {product_info.get('price', 'N/A')}")
            logger.info(f"    product_id: {product_info.get('product_id', 'N/A')}")
            logger.info(f"    product_url: {product_info.get('product_url', 'N/A')}")
        else:
            logger.info("  ✗ 추출 실패 (None 반환)")
        
        # 6. Selenium으로 직접 확인
        logger.info("\n[6] Selenium으로 직접 확인:")
        try:
            selenium_product = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["product_item"])
            selenium_link = selenium_product.find_element(By.CSS_SELECTOR, "a.gtm-select-item")
            selenium_href = selenium_link.get_attribute('href')
            selenium_data_id = selenium_link.get_attribute('data-item-id')
            logger.info(f"  Selenium으로 찾은 링크:")
            logger.info(f"    href: {selenium_href}")
            logger.info(f"    data-item-id: {selenium_data_id}")
        except Exception as e:
            logger.error(f"  Selenium 확인 실패: {e}")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        logger.error(f"분석 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    analyze_url_extraction()

