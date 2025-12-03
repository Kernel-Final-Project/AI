"""
뷰티 > 스킨케어 경로로 페이지 이동 테스트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
# TODO: navigate_to_category는 musinsa_parser에 없음
# from musinsa_parser.category_crawler import navigate_to_category

def test_navigate_beauty_skincare():
    """뷰티 > 스킨케어 경로로 이동 테스트"""
    driver = None
    try:
        driver = setup_browser(headless=False)
        
        # 카테고리 경로
        category_path = ["뷰티", "스킨케어"]
        
        logger.info("=" * 80)
        logger.info(f"카테고리 경로 테스트: {' > '.join(category_path)}")
        logger.info("=" * 80)
        
        # 카테고리로 이동
        category_url = navigate_to_category(driver, category_path)
        
        if category_url:
            logger.info(f"✓ 성공: 카테고리 페이지로 이동 완료")
            logger.info(f"  URL: {category_url}")
            logger.info(f"  현재 페이지 URL: {driver.current_url}")
            
            # 페이지 제목 확인
            page_title = driver.title
            logger.info(f"  페이지 제목: {page_title}")
            
            # 상품 목록이 있는지 확인
            try:
                # TODO: MUSINSA_SELECTORS는 musinsa_parser에 없음
                # from musinsa_parser.config import MUSINSA_SELECTORS
                product_list = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["product_list"])
                logger.info(f"  상품 목록 컨테이너 발견")
            except:
                logger.warning("  상품 목록 컨테이너를 찾을 수 없습니다")
            
            # 5초 대기 (확인용)
            logger.info("\n5초 후 브라우저 종료...")
            time.sleep(5)
        else:
            logger.error("✗ 실패: 카테고리로 이동하지 못했습니다")
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")

if __name__ == "__main__":
    test_navigate_beauty_skincare()

