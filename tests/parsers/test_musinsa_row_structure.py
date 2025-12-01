"""
무신사 카테고리 row 구조 상세 분석
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from parsers.musinsa.crawler import open_musinsa_menu
from parsers.musinsa.config import BASE_URL, MUSINSA_SELECTORS

def analyze_row_structure():
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        if not open_musinsa_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        logger.info("메뉴 열림, row 구조 분석...")
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        category_rows = modal.find_elements(By.CSS_SELECTOR, "div.CategorySubRow__StyledContainer-sc-gndfto-0")
        logger.info(f"카테고리 행: {len(category_rows)}개 발견\n")
        
        for i, row in enumerate(category_rows, 1):
            try:
                logger.info(f"=== Row {i} ===")
                
                # 모든 링크 찾기
                all_links = row.find_elements(By.TAG_NAME, "a")
                logger.info(f"  링크 개수: {len(all_links)}개")
                
                # 각 링크 정보 출력
                for j, link in enumerate(all_links[:5], 1):  # 처음 5개만
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    classes = link.get_attribute('class')
                    data_id = link.get_attribute('data-category-id')
                    
                    logger.info(f"    링크 {j}: '{text}'")
                    logger.info(f"      href: {href[:80] if href else 'None'}")
                    logger.info(f"      class: {classes[:80] if classes else 'None'}")
                    logger.info(f"      data-category-id: {data_id}")
                
                # CategorySubHeader 클래스 링크 찾기
                try:
                    header_link = row.find_element(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
                    logger.info(f"  ✓ CategorySubHeader 발견: '{header_link.text.strip()}'")
                except:
                    logger.info(f"  ✗ CategorySubHeader 없음")
                
                # 첫 번째 링크
                try:
                    first_link = row.find_element(By.CSS_SELECTOR, "a")
                    logger.info(f"  첫 번째 링크: '{first_link.text.strip()}'")
                except:
                    logger.info(f"  첫 번째 링크 없음")
                
                logger.info("")
                
            except Exception as e:
                logger.error(f"Row {i} 처리 중 오류: {e}")
                logger.info("")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    analyze_row_structure()

