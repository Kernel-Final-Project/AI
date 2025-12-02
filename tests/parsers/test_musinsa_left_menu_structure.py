"""
무신사 왼쪽 메인 카테고리 목록 구조 확인
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

def analyze_left_menu():
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        if not open_musinsa_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        logger.info("메뉴 열림, 왼쪽 메인 카테고리 구조 분석...")
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        # 방법 1: 모든 링크 찾기
        all_links = modal.find_elements(By.TAG_NAME, "a")
        logger.info(f"\n=== 모든 링크: {len(all_links)}개 ===")
        
        main_categories = set()
        for i, link in enumerate(all_links[:50], 1):  # 처음 50개만
            text = link.text.strip()
            href = link.get_attribute('href')
            classes = link.get_attribute('class')
            
            if text and href:
                logger.info(f"{i}. 텍스트: '{text}' | href: {href[:80]} | class: {classes}")
                if '/main/' in href and text not in ["전체", "남성", "여성"]:
                    main_categories.add(text)
        
        logger.info(f"\n=== /main/ 패턴을 가진 메인 카테고리 후보: {len(main_categories)}개 ===")
        for cat in sorted(main_categories):
            logger.info(f"  - {cat}")
        
        # 방법 2: 특정 클래스 찾기
        logger.info(f"\n=== CategorySubHeader 클래스 링크 ===")
        header_links = modal.find_elements(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
        logger.info(f"발견: {len(header_links)}개")
        for i, link in enumerate(header_links, 1):
            text = link.text.strip()
            href = link.get_attribute('href')
            logger.info(f"{i}. '{text}' | {href[:80] if href else 'None'}")
        
        # 방법 3: 왼쪽 영역 찾기 (특정 컨테이너나 클래스)
        logger.info(f"\n=== 모달 내부 구조 분석 ===")
        # 모달의 직접 자식 요소들 확인
        modal_children = driver.execute_script("""
            var modal = arguments[0];
            var children = [];
            for (var i = 0; i < modal.children.length; i++) {
                var child = modal.children[i];
                children.push({
                    tagName: child.tagName,
                    className: child.className,
                    id: child.id,
                    textContent: child.textContent ? child.textContent.substring(0, 50) : ''
                });
            }
            return children;
        """, modal)
        
        logger.info(f"모달 직접 자식 요소: {len(modal_children)}개")
        for i, child in enumerate(modal_children, 1):
            logger.info(f"{i}. {child['tagName']} | class: {child['className'][:80]} | id: {child['id']}")
        
        # 방법 4: 왼쪽 메뉴 영역 찾기 (일반적인 네비게이션 구조)
        logger.info(f"\n=== 왼쪽 메뉴 영역 찾기 ===")
        # nav, ul, li 등의 구조 찾기
        nav_elements = modal.find_elements(By.TAG_NAME, "nav")
        ul_elements = modal.find_elements(By.TAG_NAME, "ul")
        logger.info(f"nav 요소: {len(nav_elements)}개, ul 요소: {len(ul_elements)}개")
        
        # 방법 5: data 속성이나 특정 패턴 찾기
        logger.info(f"\n=== data-category-id 속성 가진 링크 ===")
        links_with_data = modal.find_elements(By.CSS_SELECTOR, "a[data-category-id]")
        logger.info(f"발견: {len(links_with_data)}개")
        for i, link in enumerate(links_with_data[:20], 1):
            text = link.text.strip()
            data_id = link.get_attribute('data-category-id')
            href = link.get_attribute('href')
            logger.info(f"{i}. '{text}' | data-category-id: {data_id} | href: {href[:80] if href else 'None'}")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    analyze_left_menu()

