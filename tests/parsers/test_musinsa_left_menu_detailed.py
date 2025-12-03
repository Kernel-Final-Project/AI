"""
무신사 왼쪽 메인 카테고리 목록 상세 분석
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

def analyze_left_menu_detailed():
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        if not open_musinsa_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        logger.info("메뉴 열림, 왼쪽 메인 카테고리 상세 분석...")
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        # CategoryMenu__Contents 영역 찾기 (모달의 3번째 자식)
        contents = modal.find_element(By.CSS_SELECTOR, "div.CategoryMenu__Contents-sc-1vgk8ts-0")
        
        # 왼쪽 영역 찾기 (일반적으로 첫 번째 컬럼)
        # JavaScript로 DOM 구조 확인
        left_menu_structure = driver.execute_script("""
            var contents = arguments[0];
            var structure = [];
            
            // 모든 div 요소 찾기
            var divs = contents.querySelectorAll('div');
            for (var i = 0; i < divs.length; i++) {
                var div = divs[i];
                var text = div.textContent ? div.textContent.trim().substring(0, 30) : '';
                var className = div.className || '';
                var children = div.children.length;
                
                // 왼쪽 메뉴 후보: 자식이 많고 특정 클래스를 가진 div
                if (children > 0 || text.length > 0) {
                    structure.push({
                        index: i,
                        tagName: div.tagName,
                        className: className.substring(0, 100),
                        textContent: text,
                        childrenCount: children,
                        html: div.outerHTML.substring(0, 200)
                    });
                }
            }
            return structure;
        """, contents)
        
        logger.info(f"\n=== CategoryMenu__Contents 내부 구조: {len(left_menu_structure)}개 요소 ===")
        for i, elem in enumerate(left_menu_structure[:30], 1):
            logger.info(f"{i}. {elem['tagName']} | children: {elem['childrenCount']} | class: {elem['className'][:60]}")
            logger.info(f"   text: {elem['textContent']}")
        
        # 방법: data-category-id를 가진 링크 중에서 /main/ 패턴이 아닌 것들도 확인
        # 왼쪽 메인 카테고리는 /category/001 같은 패턴일 수도 있음
        logger.info(f"\n=== 모든 링크 분석 (href 패턴별) ===")
        all_links = modal.find_elements(By.TAG_NAME, "a")
        
        # 패턴별 분류
        main_pattern_links = []  # /main/ 패턴
        category_pattern_links = []  # /category/ 패턴 (상위 카테고리일 수 있음)
        other_links = []
        
        for link in all_links:
            href = link.get_attribute('href')
            text = link.text.strip()
            classes = link.get_attribute('class')
            
            if not href or not text:
                continue
                
            if '/main/' in href:
                main_pattern_links.append((text, href, classes))
            elif '/category/' in href:
                # 카테고리 ID가 짧은 것 (001, 002 등)은 메인 카테고리일 수 있음
                category_id = href.split('/category/')[-1].split('?')[0]
                if len(category_id) <= 3:  # 001, 002 같은 짧은 ID
                    category_pattern_links.append((text, href, category_id, classes))
            else:
                other_links.append((text, href, classes))
        
        logger.info(f"\n/main/ 패턴 링크: {len(main_pattern_links)}개")
        for text, href, classes in main_pattern_links:
            logger.info(f"  - '{text}' | {href} | class: {classes[:60]}")
        
        logger.info(f"\n/category/ 패턴 링크 (짧은 ID, 메인 카테고리 후보): {len(category_pattern_links)}개")
        seen_ids = set()
        for text, href, cat_id, classes in category_pattern_links:
            if cat_id not in seen_ids and text not in ["전체 보기"]:
                seen_ids.add(cat_id)
                logger.info(f"  - '{text}' | ID: {cat_id} | {href} | class: {classes[:60]}")
        
        # 실제 왼쪽 메뉴 영역 찾기
        logger.info(f"\n=== 왼쪽 메뉴 영역 직접 찾기 ===")
        # CategorySubRow__StyledContainer를 찾아서 그 안의 첫 번째 링크가 메인일 수 있음
        rows = modal.find_elements(By.CSS_SELECTOR, "div.CategorySubRow__StyledContainer-sc-gndfto-0")
        logger.info(f"CategorySubRow 발견: {len(rows)}개")
        
        main_categories_from_rows = []
        for i, row in enumerate(rows[:20], 1):  # 처음 20개만
            try:
                # 각 row의 첫 번째 링크가 메인 카테고리일 수 있음
                first_link = row.find_element(By.CSS_SELECTOR, "a")
                text = first_link.text.strip()
                href = first_link.get_attribute('href')
                classes = first_link.get_attribute('class')
                
                if text and text not in ["전체 보기"]:
                    main_categories_from_rows.append((text, href, classes))
                    logger.info(f"{i}. '{text}' | {href[:80] if href else 'None'} | class: {classes[:60]}")
            except:
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
    analyze_left_menu_detailed()
