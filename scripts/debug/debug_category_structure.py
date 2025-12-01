"""
카테고리 구조 디버깅 - 왜 일부 카테고리는 1단계만 탐색되는지 확인
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from parsers.ssadagu.crawler import open_ssadagu_menu
from parsers.ssadagu.config import BASE_URL


def debug_category_structure():
    """
    각 카테고리의 실제 구조를 확인
    """
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 전체카테고리 메뉴 열기
        if not open_ssadagu_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        # 1단계 카테고리 찾기
        dep1_links = driver.find_elements(By.CSS_SELECTOR, "ul.dep_1cover.link_cover > li.dep_1 > a.cate_tit")
        logger.info(f"1단계 카테고리: {len(dep1_links)}개 발견\n")
        
        # 문제가 되는 카테고리들 확인
        problem_categories = ["신발/가방/패션잡화", "스포츠/레저", "홈인테리어", "펫 용품"]
        
        for i, dep1_link in enumerate(dep1_links, 1):
            dep1_name = dep1_link.text.strip()
            if not dep1_name:
                continue
            
            # 문제 카테고리만 상세 분석
            if dep1_name not in problem_categories:
                continue
            
            print("=" * 80)
            print(f"[{i}] {dep1_name}")
            print("=" * 80)
            
            # 1단계에 hover
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", dep1_link
            )
            time.sleep(0.3)
            
            ActionChains(driver).move_to_element(dep1_link).perform()
            time.sleep(1.0)  # 충분한 대기 시간
            
            # 2단계 메뉴 확인
            print("\n1. 2단계 메뉴 컨테이너 찾기 시도...")
            try:
                dep2_container = driver.find_element(By.CSS_SELECTOR, "div.dep_2cover")
                print(f"   ✅ dep_2cover 요소 발견")
                
                # 여러 방법으로 visibility 확인
                visibility = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).visibility;",
                    dep2_container
                )
                display = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).display;",
                    dep2_container
                )
                opacity = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).opacity;",
                    dep2_container
                )
                
                print(f"   - visibility: {visibility}")
                print(f"   - display: {display}")
                print(f"   - opacity: {opacity}")
                
                # 실제로 보이는지 확인
                is_displayed = dep2_container.is_displayed()
                print(f"   - is_displayed(): {is_displayed}")
                
                # 2단계 링크 찾기 시도
                try:
                    dep2_links = dep2_container.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
                    print(f"   - 2단계 링크 개수: {len(dep2_links)}개")
                    
                    if dep2_links:
                        print(f"   - 2단계 카테고리 목록:")
                        for j, link in enumerate(dep2_links[:5], 1):  # 처음 5개만
                            print(f"     {j}. {link.text.strip()}")
                        if len(dep2_links) > 5:
                            print(f"     ... 외 {len(dep2_links) - 5}개")
                    
                    # 2단계 링크가 있으면 3단계도 확인
                    if dep2_links:
                        print(f"\n2. 첫 번째 2단계 항목에 hover하여 3단계 확인...")
                        first_dep2 = dep2_links[0]
                        dep2_name = first_dep2.text.strip()
                        print(f"   - 선택한 2단계: {dep2_name}")
                        
                        ActionChains(driver).move_to_element(first_dep2).perform()
                        time.sleep(1.0)
                        
                        # 3단계 컨테이너 찾기
                        try:
                            dep2_parent = first_dep2.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_2')]")
                            dep3_container = dep2_parent.find_element(By.CSS_SELECTOR, "div.dep_3cover")
                            
                            dep3_visibility = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).visibility;",
                                dep3_container
                            )
                            dep3_display = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).display;",
                                dep3_container
                            )
                            
                            print(f"   ✅ dep_3cover 요소 발견")
                            print(f"   - visibility: {dep3_visibility}")
                            print(f"   - display: {dep3_display}")
                            
                            dep3_links = dep3_container.find_elements(By.CSS_SELECTOR, "li.dep_3 > a.cate_tit")
                            print(f"   - 3단계 링크 개수: {len(dep3_links)}개")
                            
                            if dep3_links:
                                print(f"   - 3단계 카테고리 목록 (처음 5개):")
                                for k, link in enumerate(dep3_links[:5], 1):
                                    print(f"     {k}. {link.text.strip()}")
                                
                        except Exception as e:
                            print(f"   ❌ 3단계 찾기 실패: {e}")
                            
                except Exception as e:
                    print(f"   ❌ 2단계 링크 찾기 실패: {e}")
                
            except Exception as e:
                print(f"   ❌ dep_2cover 요소를 찾을 수 없음: {e}")
                print(f"   → 이 카테고리는 2단계가 없거나 다른 구조를 사용하는 것 같습니다")
            
            print()
            
            # 메뉴 다시 열기
            if not open_ssadagu_menu(driver):
                print("   ⚠️  메뉴 재오픈 실패")
            time.sleep(0.5)
        
        print("\n" + "=" * 80)
        print("분석 완료")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            input("\n브라우저를 확인한 후 Enter를 눌러 종료하세요...")
            driver.quit()


if __name__ == "__main__":
    debug_category_structure()



