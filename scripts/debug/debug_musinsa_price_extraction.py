"""
무신사 가격 추출 원인 분석
할인율과 가격이 혼동되는 문제 확인
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from parsers.musinsa.crawler import navigate_to_category
from parsers.musinsa.config import MUSINSA_SELECTORS

def analyze_price_extraction():
    """가격 추출 실패 원인 분석"""
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
        
        # 상품 요소들 찾기
        product_elements = product_list.select(MUSINSA_SELECTORS["product_item"])
        if not product_elements:
            logger.error("상품 요소를 찾을 수 없습니다")
            return
        
        logger.info(f"상품 요소 {len(product_elements)}개 발견\n")
        
        # 할인된 제품과 할인 안 된 제품 각각 분석
        for i, product in enumerate(product_elements[:5], 1):
            logger.info("=" * 80)
            logger.info(f"상품 {i} 분석")
            logger.info("=" * 80)
            
            # 가격 요소 찾기
            price_elem = product.select_one(MUSINSA_SELECTORS["product_price"])
            if not price_elem:
                logger.info("  ✗ 가격 요소를 찾을 수 없습니다")
                continue
            
            logger.info("\n[1] 가격 요소 전체 HTML:")
            logger.info(str(price_elem))
            
            logger.info("\n[2] 가격 요소 전체 텍스트:")
            full_text = price_elem.get_text(strip=True)
            logger.info(f"  '{full_text}'")
            
            logger.info("\n[3] 모든 span 요소 분석:")
            all_spans = price_elem.select("span")
            logger.info(f"  span 개수: {len(all_spans)}개")
            
            for j, span in enumerate(all_spans, 1):
                span_text = span.get_text(strip=True)
                span_classes = span.get('class', [])
                has_text_red = 'text-red' in ' '.join(span_classes)
                has_won = '원' in span_text
                has_percent = '%' in span_text
                
                logger.info(f"\n  Span {j}:")
                logger.info(f"    텍스트: '{span_text}'")
                logger.info(f"    클래스: {span_classes}")
                logger.info(f"    text-red 포함: {has_text_red}")
                logger.info(f"    '원' 포함: {has_won}")
                logger.info(f"    '%' 포함: {has_percent}")
                
                # 현재 로직으로 판단
                if has_text_red:
                    logger.info(f"    → 할인율로 판단")
                elif has_won:
                    logger.info(f"    → 가격으로 판단 (원 포함)")
                else:
                    logger.info(f"    → 기타")
            
            logger.info("\n[4] 현재 로직으로 추출한 가격:")
            # 현재 extract_product_info 함수 테스트
            from parsers.musinsa.product_extractor import extract_product_info
            product_info = extract_product_info(product)
            if product_info:
                logger.info(f"  추출된 가격: '{product_info.get('price', 'N/A')}'")
            else:
                logger.info("  ✗ 추출 실패")
            
            logger.info("\n[5] '원' 포함 여부 확인:")
            if '원' in full_text:
                logger.info(f"  ✓ '원'이 포함되어 있음")
                # '원'이 포함된 부분 찾기
                import re
                won_matches = re.findall(r'[\d,]+원', full_text)
                logger.info(f"  '원'이 포함된 숫자: {won_matches}")
            else:
                logger.info(f"  ✗ '원'이 포함되어 있지 않음")
            
            logger.info("\n")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        logger.error(f"분석 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    analyze_price_extraction()

