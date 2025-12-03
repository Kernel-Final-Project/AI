"""
무신사 하위 카테고리 구조 확인
메인 카테고리를 클릭했을 때 오른쪽에 나타나는 하위 카테고리 영역 분석
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
# TODO: open_musinsa_menu는 musinsa_parser에 없음. open_musinsa_category_panel 사용 필요
# from musinsa_parser.category_crawler import open_musinsa_category_panel as open_musinsa_menu
from musinsa_parser.config import BASE_URL
# TODO: MUSINSA_SELECTORS는 musinsa_parser에 없음. XPath 사용
# from musinsa_parser.config import MUSINSA_SELECTORS

def analyze_subcategory_structure():
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        if not open_musinsa_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        logger.info("메뉴 열림, 하위 카테고리 구조 분석...")
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        # 왼쪽 메인 카테고리 찾기
        main_menu_container = modal.find_element(By.CSS_SELECTOR, "div.MainMenu__StyledContainer-sc-1v9l62g-0")
        main_menu_rows = main_menu_container.find_elements(By.CSS_SELECTOR, "p.MainMenuRow__Container-sc-ck8m2r-0")
        
        logger.info(f"메인 카테고리: {len(main_menu_rows)}개 발견\n")
        
        # 몇 개 메인 카테고리만 테스트 (처음 3개)
        for i, main_row in enumerate(main_menu_rows[:3], 1):
            try:
                # 메인 카테고리 이름
                main_name = main_row.get_attribute('data-category-name') or main_row.text.strip()
                logger.info(f"{'='*80}")
                logger.info(f"메인 카테고리 {i}: {main_name}")
                logger.info(f"{'='*80}")
                
                # 메인 카테고리 클릭
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", main_row)
                time.sleep(0.3)
                main_row.click()
                time.sleep(0.8)  # 하위 카테고리 로드 대기
                
                # 업데이트된 모달에서 하위 카테고리 영역 찾기
                updated_modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
                
                # 오른쪽 하위 카테고리 영역 찾기
                # CategorySubRow__StyledContainer 또는 다른 컨테이너 찾기
                logger.info(f"\n[하위 카테고리 영역 구조 분석]")
                
                # 방법 1: CategorySubRow__StyledContainer 찾기
                sub_rows = updated_modal.find_elements(By.CSS_SELECTOR, "div.CategorySubRow__StyledContainer-sc-gndfto-0")
                logger.info(f"CategorySubRow 발견: {len(sub_rows)}개")
                
                if sub_rows:
                    for j, sub_row in enumerate(sub_rows[:1], 1):  # 첫 번째 row만 상세 분석
                        logger.info(f"\n  --- SubRow {j} 구조 ---")
                        
                        # 모든 링크 찾기
                        all_links = sub_row.find_elements(By.TAG_NAME, "a")
                        logger.info(f"    링크 개수: {len(all_links)}개")
                        
                        # 처음 10개 링크 정보
                        for k, link in enumerate(all_links[:10], 1):
                            text = link.text.strip()
                            href = link.get_attribute('href')
                            classes = link.get_attribute('class')
                            data_id = link.get_attribute('data-category-id')
                            
                            logger.info(f"    링크 {k}: '{text}'")
                            logger.info(f"      href: {href[:80] if href else 'None'}")
                            logger.info(f"      class: {classes[:80] if classes else 'None'}")
                            logger.info(f"      data-category-id: {data_id}")
                
                # 방법 2: CategorySubItem__StyledContainer 찾기
                sub_items = updated_modal.find_elements(By.CSS_SELECTOR, "a.CategorySubItem__StyledContainer-sc-1kgwyy5-0")
                logger.info(f"\nCategorySubItem 링크 발견: {len(sub_items)}개")
                
                if sub_items:
                    logger.info(f"처음 10개 하위 카테고리:")
                    for k, item in enumerate(sub_items[:10], 1):
                        text = item.text.strip()
                        href = item.get_attribute('href')
                        data_id = item.get_attribute('data-category-id')
                        logger.info(f"  {k}. '{text}' | ID: {data_id} | {href[:60] if href else 'None'}")
                
                # 방법 3: 전체 보기 링크 찾기
                all_view_links = updated_modal.find_elements(By.XPATH, ".//a[text()='전체 보기']")
                logger.info(f"\n'전체 보기' 링크: {len(all_view_links)}개")
                if all_view_links:
                    for k, link in enumerate(all_view_links[:3], 1):
                        href = link.get_attribute('href')
                        data_id = link.get_attribute('data-category-id')
                        logger.info(f"  {k}. href: {href} | data-category-id: {data_id}")
                
                logger.info("\n")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"메인 카테고리 {i} 처리 중 오류: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    analyze_subcategory_structure()

