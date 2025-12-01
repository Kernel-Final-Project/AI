"""
3단계 카테고리를 못 찾는 원인 분석
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


def debug_level3_categories():
    """
    3단계 카테고리를 못 찾는 원인 상세 분석
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
        
        # 문제가 되는 카테고리들 확인 (2단계는 찾지만 3단계를 못 찾는 것들)
        problem_categories = [
            ("신발/가방/패션잡화", "여성슈즈"),
            ("신발/가방/패션잡화", "남성슈즈"),
            ("스포츠/레저", "스포츠용품"),
        ]
        
        # 1단계 카테고리 찾기
        dep1_links = driver.find_elements(By.CSS_SELECTOR, "ul.dep_1cover.link_cover > li.dep_1 > a.cate_tit")
        
        for dep1_link in dep1_links:
            dep1_name = dep1_link.text.strip()
            if not dep1_name:
                continue
            
            # 문제 카테고리만 분석
            matching_problems = [p for p in problem_categories if p[0] == dep1_name]
            if not matching_problems:
                continue
            
            print("=" * 80)
            print(f"[1단계] {dep1_name}")
            print("=" * 80)
            
            # 1단계에 hover
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", dep1_link
            )
            time.sleep(0.3)
            
            ActionChains(driver).move_to_element(dep1_link).perform()
            time.sleep(1.5)
            
            # 2단계 메뉴 확인
            try:
                dep2_container = driver.find_element(By.CSS_SELECTOR, "div.dep_2cover")
                
                # JavaScript로 강제 표시 (필요시)
                dep2_visible = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).visibility;",
                    dep2_container
                )
                dep2_display = driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).display;",
                    dep2_container
                )
                
                if dep2_display == "none":
                    driver.execute_script(
                        "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';",
                        dep2_container
                    )
                    time.sleep(0.5)
                
                # 2단계 링크 찾기
                dep2_links_all = dep2_container.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
                dep2_links = [link for link in dep2_links_all if link.text.strip()]
                
                print(f"\n2단계 카테고리: {len(dep2_links)}개 발견")
                print(f"2단계 목록:")
                for link in dep2_links:
                    print(f"  - {link.text.strip()}")
                
                # 모든 2단계 항목에 대해 3단계 확인 (매칭 여부와 관계없이)
                for dep2_link in dep2_links:
                    dep2_name = dep2_link.text.strip()
                    
                    print(f"\n{'=' * 80}")
                    print(f"[2단계] {dep2_name}")
                    print(f"{'=' * 80}")
                    
                    print(f"\n{'=' * 80}")
                    print(f"[2단계] {dep2_name}")
                    print(f"{'=' * 80}")
                    
                    # 2단계에 hover
                    print(f"\n1. 2단계 항목에 hover 시작...")
                    ActionChains(driver).move_to_element(dep2_link).perform()
                    time.sleep(1.5)  # 충분한 대기
                    
                    # 2단계 항목의 부모 li 찾기
                    print(f"\n2. 부모 li 요소 찾기...")
                    try:
                        dep2_parent = dep2_link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_2')]")
                        print(f"   ✅ 부모 li 발견: {dep2_parent.get_attribute('class')}")
                        
                        # 부모 li 내에서 dep_3cover 찾기
                        print(f"\n3. dep_3cover 요소 찾기...")
                        try:
                            dep3_container = dep2_parent.find_element(By.CSS_SELECTOR, "div.dep_3cover")
                            print(f"   ✅ dep_3cover 요소 발견")
                            
                            # CSS 속성 확인
                            print(f"\n4. CSS 속성 확인...")
                            dep3_visible = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).visibility;",
                                dep3_container
                            )
                            dep3_display = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).display;",
                                dep3_container
                            )
                            dep3_opacity = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).opacity;",
                                dep3_container
                            )
                            dep3_height = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).height;",
                                dep3_container
                            )
                            dep3_width = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).width;",
                                dep3_container
                            )
                            
                            print(f"   - visibility: {dep3_visible}")
                            print(f"   - display: {dep3_display}")
                            print(f"   - opacity: {dep3_opacity}")
                            print(f"   - height: {dep3_height}")
                            print(f"   - width: {dep3_width}")
                            
                            is_displayed = dep3_container.is_displayed()
                            print(f"   - is_displayed(): {is_displayed}")
                            
                            # 위치 정보
                            location = dep3_container.location
                            size = dep3_container.size
                            print(f"   - location: {location}")
                            print(f"   - size: {size}")
                            
                            # HTML 구조 확인
                            print(f"\n5. HTML 구조 확인...")
                            html_snippet = driver.execute_script(
                                "return arguments[0].outerHTML.substring(0, 500);",
                                dep3_container
                            )
                            print(f"   HTML (처음 500자):\n   {html_snippet}")
                            
                            # 3단계 링크 찾기 시도
                            print(f"\n6. 3단계 링크 찾기...")
                            
                            # 방법 1: 일반 선택자
                            dep3_links_method1 = dep3_container.find_elements(By.CSS_SELECTOR, "li.dep_3 > a.cate_tit")
                            print(f"   방법 1 (li.dep_3 > a.cate_tit): {len(dep3_links_method1)}개")
                            
                            # 방법 2: 더 넓은 선택자
                            dep3_links_method2 = dep3_container.find_elements(By.CSS_SELECTOR, "a.cate_tit")
                            print(f"   방법 2 (a.cate_tit): {len(dep3_links_method2)}개")
                            
                            # 방법 3: 모든 링크
                            dep3_links_method3 = dep3_container.find_elements(By.TAG_NAME, "a")
                            print(f"   방법 3 (모든 a 태그): {len(dep3_links_method3)}개")
                            
                            # 방법 4: JavaScript로 직접 찾기
                            dep3_links_js = driver.execute_script("""
                                var container = arguments[0];
                                var links = container.querySelectorAll('li.dep_3 > a.cate_tit');
                                var result = [];
                                for (var i = 0; i < links.length; i++) {
                                    result.push({
                                        text: links[i].textContent.trim(),
                                        href: links[i].href
                                    });
                                }
                                return result;
                            """, dep3_container)
                            print(f"   방법 4 (JavaScript): {len(dep3_links_js)}개")
                            
                            if dep3_links_js:
                                print(f"   JavaScript로 찾은 링크들:")
                                for i, link_info in enumerate(dep3_links_js[:5], 1):
                                    print(f"     {i}. {link_info['text']} ({link_info['href'][:80]}...)")
                            
                            # 텍스트가 있는 링크만 필터링
                            valid_links = [link for link in dep3_links_method1 if link.text.strip()]
                            print(f"\n   텍스트가 있는 링크: {len(valid_links)}개")
                            
                            if valid_links:
                                print(f"   유효한 링크 목록:")
                                for i, link in enumerate(valid_links[:5], 1):
                                    print(f"     {i}. {link.text.strip()}")
                            
                            # 조건 체크
                            print(f"\n7. 조건 체크 결과...")
                            condition1 = dep3_visible == "visible"
                            condition2 = dep3_display != "none"
                            condition3 = is_displayed
                            
                            print(f"   - visibility == 'visible': {condition1}")
                            print(f"   - display != 'none': {condition2}")
                            print(f"   - is_displayed(): {condition3}")
                            print(f"   - 모든 조건 만족: {condition1 and condition2 and condition3}")
                            
                            if not (condition1 and condition2 and condition3):
                                print(f"\n   ❌ 조건을 만족하지 않아서 3단계를 찾지 못함!")
                                print(f"   → 이게 문제의 원인일 가능성이 높습니다.")
                            
                            if not valid_links:
                                print(f"\n   ❌ 텍스트가 있는 링크가 없어서 3단계를 찾지 못함!")
                                print(f"   → 링크는 있지만 텍스트가 비어있을 수 있습니다.")
                            
                        except Exception as e:
                            print(f"   ❌ dep_3cover 요소를 찾을 수 없음: {e}")
                            print(f"   → 이 2단계 항목에는 3단계가 없거나 다른 구조일 수 있습니다.")
                            
                    except Exception as e:
                        print(f"   ❌ 부모 li 요소를 찾을 수 없음: {e}")
                        import traceback
                        print(traceback.format_exc())
                
                # 메뉴 다시 열기
                if not open_ssadagu_menu(driver):
                    print("   ⚠️  메뉴 재오픈 실패")
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ 2단계 메뉴를 찾을 수 없음: {e}")
        
        print("\n" + "=" * 80)
        print("분석 완료")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"디버깅 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            time.sleep(3)  # 브라우저 확인을 위한 대기
            driver.quit()


if __name__ == "__main__":
    debug_level3_categories()

