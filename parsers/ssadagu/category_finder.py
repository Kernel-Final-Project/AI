"""
싸다구 사이트의 모든 카테고리 경로를 찾는 모듈
"""
from typing import List, Dict
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


def find_all_category_paths() -> List[List[str]]:
    """
    싸다구 사이트의 모든 카테고리 경로를 찾아서 반환
    
    Returns:
        카테고리 경로 리스트의 리스트
        예: [
            ["패션의류/이너웨어", "남성의류", "셔츠"],
            ["패션의류/이너웨어", "남성의류", "티셔츠"],
            ...
        ]
    """
    logger.info("모든 카테고리 경로 찾기 시작")
    
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 전체카테고리 메뉴 열기
        trigger = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.all_cate i.fa-bars"))
        )
        
        if not open_ssadagu_menu(driver):
            logger.error("메뉴 열기 실패")
            return []
        
        logger.info("메뉴 열림, 카테고리 경로 탐색 시작...")
        
        all_paths = []
        
        # 1단계 카테고리 찾기
        dep1_links = driver.find_elements(By.CSS_SELECTOR, "ul.dep_1cover.link_cover > li.dep_1 > a.cate_tit")
        logger.info(f"1단계 카테고리: {len(dep1_links)}개 발견")
        
        for i, dep1_link in enumerate(dep1_links, 1):
            try:
                dep1_name = dep1_link.text.strip()
                if not dep1_name:
                    continue
                
                logger.info(f"[1단계 {i}/{len(dep1_links)}] {dep1_name}")
                
                # 1단계에 hover
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", dep1_link
                )
                time.sleep(0.3)
                
                ActionChains(driver).move_to_element(dep1_link).perform()
                time.sleep(1.2)  # 더 긴 대기 시간
                
                # 2단계 메뉴가 열렸는지 확인
                # 중요: 현재 hover한 1단계 카테고리의 부모 li 내부에서만 dep_2cover 찾기
                try:
                    # 현재 1단계 링크의 부모 li 찾기
                    dep1_parent = dep1_link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_1')]")
                    # 부모 li 내부의 dep_2cover 찾기
                    dep2_container = dep1_parent.find_element(By.CSS_SELECTOR, "div.dep_2cover")
                    
                    # visibility와 display 모두 체크
                    dep2_visible = driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).visibility;",
                        dep2_container
                    )
                    dep2_display = driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).display;",
                        dep2_container
                    )
                    
                    # is_displayed()도 체크
                    is_displayed = dep2_container.is_displayed()
                    
                    # 모든 조건 확인: visibility가 visible이고, display가 none이 아니고, is_displayed()가 True
                    if dep2_visible == "visible" and dep2_display != "none" and is_displayed:
                        # 2단계 메뉴 내부로 커서 이동
                        try:
                            first_dep2 = dep2_container.find_element(By.CSS_SELECTOR, "a.cate_tit")
                            ActionChains(driver).move_to_element(first_dep2).perform()
                            time.sleep(0.5)
                        except:
                            ActionChains(driver).move_to_element(dep2_container).perform()
                            time.sleep(0.5)
                        
                        # 2단계 카테고리 찾기 (텍스트가 있는 링크만)
                        # 중요: dep2_container 내부에서만 찾기
                        dep2_links_all = dep2_container.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
                        dep2_links = [link for link in dep2_links_all if link.text.strip()]  # 텍스트가 있는 것만
                        logger.info(f"  → 2단계 카테고리: {len(dep2_links)}개 (전체 {len(dep2_links_all)}개 중)")
                        
                        for j, dep2_link in enumerate(dep2_links, 1):
                            try:
                                dep2_name = dep2_link.text.strip()
                                if not dep2_name:
                                    continue
                                
                                logger.info(f"  [2단계 {j}/{len(dep2_links)}] {dep2_name}")
                                
                                # 2단계에 hover
                                ActionChains(driver).move_to_element(dep2_link).perform()
                                time.sleep(1.0)  # 더 긴 대기 시간
                                
                                # 3단계 메뉴가 열렸는지 확인
                                # 2단계 항목의 부모 li 요소 내에서 dep_3cover 찾기
                                try:
                                    dep2_parent = dep2_link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_2')]")
                                    dep3_container = dep2_parent.find_element(By.CSS_SELECTOR, "div.dep_3cover")
                                    dep3_visible = driver.execute_script(
                                        "return window.getComputedStyle(arguments[0]).visibility;",
                                        dep3_container
                                    )
                                    
                                    # visibility가 visible이면 JavaScript로 텍스트 가져오기 (display: none이어도 가능)
                                    if dep3_visible == "visible":
                                        # JavaScript로 3단계 카테고리 텍스트 가져오기 (display: none이어도 작동)
                                        dep3_names = driver.execute_script("""
                                            var container = arguments[0];
                                            var links = container.querySelectorAll('li.dep_3 > a.cate_tit');
                                            var result = [];
                                            for (var i = 0; i < links.length; i++) {
                                                var text = links[i].textContent.trim();
                                                if (text) {
                                                    result.push(text);
                                                }
                                            }
                                            return result;
                                        """, dep3_container)
                                        
                                        if dep3_names:
                                            logger.info(f"    → 3단계 카테고리: {len(dep3_names)}개 (JavaScript로 찾음)")
                                            for dep3_name in dep3_names:
                                                # 3단계까지 있는 경로
                                                path = [dep1_name, dep2_name, dep3_name]
                                                all_paths.append(path)
                                                logger.debug(f"      경로 추가: {' > '.join(path)}")
                                        else:
                                            # 3단계가 없으면 2단계까지만
                                            path = [dep1_name, dep2_name]
                                            all_paths.append(path)
                                            logger.debug(f"    경로 추가 (2단계까지만): {' > '.join(path)}")
                                    else:
                                        # 3단계가 없으면 2단계까지만
                                        path = [dep1_name, dep2_name]
                                        all_paths.append(path)
                                        logger.debug(f"    경로 추가 (2단계까지만): {' > '.join(path)}")
                                        
                                except Exception as e:
                                    # 3단계가 없으면 2단계까지만
                                    path = [dep1_name, dep2_name]
                                    all_paths.append(path)
                                    logger.debug(f"    경로 추가 (2단계까지만, 예외: {e}): {' > '.join(path)}")
                                    
                            except Exception as e:
                                logger.debug(f"  2단계 처리 중 오류: {e}")
                                continue
                    else:
                        # 2단계가 보이지 않으면 추가 확인
                        logger.debug(f"  2단계 메뉴가 보이지 않음 (visibility: {dep2_visible}, display: {dep2_display}, is_displayed: {is_displayed})")
                        
                        # JavaScript로 강제 표시 시도
                        try:
                            driver.execute_script(
                                "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';",
                                dep2_container
                            )
                            time.sleep(0.5)
                            
                            # 다시 체크
                            dep2_visible_after = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).visibility;",
                                dep2_container
                            )
                            dep2_display_after = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).display;",
                                dep2_container
                            )
                            is_displayed_after = dep2_container.is_displayed()
                            
                            if dep2_visible_after == "visible" and dep2_display_after != "none" and is_displayed_after:
                                logger.info(f"  → JavaScript로 표시 성공, 2단계 탐색 재시도")
                                # 2단계 메뉴 내부로 커서 이동
                                try:
                                    first_dep2 = dep2_container.find_element(By.CSS_SELECTOR, "a.cate_tit")
                                    ActionChains(driver).move_to_element(first_dep2).perform()
                                    time.sleep(0.5)
                                except:
                                    ActionChains(driver).move_to_element(dep2_container).perform()
                                    time.sleep(0.5)
                                
                                # 2단계 카테고리 찾기 (dep2_container 내부에서만)
                                dep2_links_all = dep2_container.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
                                dep2_links = [link for link in dep2_links_all if link.text.strip()]
                                
                                if dep2_links:
                                    logger.info(f"  → 2단계 카테고리 (강제 표시 후): {len(dep2_links)}개")
                                    # 2단계 처리 로직 (위의 if 블록과 동일)
                                    for j, dep2_link in enumerate(dep2_links, 1):
                                        try:
                                            dep2_name = dep2_link.text.strip()
                                            if not dep2_name:
                                                continue
                                            
                                            logger.info(f"  [2단계 {j}/{len(dep2_links)}] {dep2_name}")
                                            
                                            # 2단계에 hover
                                            ActionChains(driver).move_to_element(dep2_link).perform()
                                            time.sleep(1.0)
                                            
                                            # 3단계 메뉴 확인
                                            try:
                                                dep2_parent = dep2_link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_2')]")
                                                dep3_container = dep2_parent.find_element(By.CSS_SELECTOR, "div.dep_3cover")
                                                dep3_visible = driver.execute_script(
                                                    "return window.getComputedStyle(arguments[0]).visibility;",
                                                    dep3_container
                                                )
                                                
                                                if dep3_visible == "visible":
                                                    dep3_names = driver.execute_script("""
                                                        var container = arguments[0];
                                                        var links = container.querySelectorAll('li.dep_3 > a.cate_tit');
                                                        var result = [];
                                                        for (var i = 0; i < links.length; i++) {
                                                            var text = links[i].textContent.trim();
                                                            if (text) {
                                                                result.push(text);
                                                            }
                                                        }
                                                        return result;
                                                    """, dep3_container)
                                                    
                                                    if dep3_names:
                                                        logger.info(f"    → 3단계 카테고리: {len(dep3_names)}개 (JavaScript로 찾음)")
                                                        for dep3_name in dep3_names:
                                                            path = [dep1_name, dep2_name, dep3_name]
                                                            all_paths.append(path)
                                                            logger.debug(f"      경로 추가: {' > '.join(path)}")
                                                    else:
                                                        path = [dep1_name, dep2_name]
                                                        all_paths.append(path)
                                                        logger.debug(f"    경로 추가 (2단계까지만): {' > '.join(path)}")
                                                else:
                                                    path = [dep1_name, dep2_name]
                                                    all_paths.append(path)
                                                    logger.debug(f"    경로 추가 (2단계까지만): {' > '.join(path)}")
                                                    
                                            except Exception as e:
                                                path = [dep1_name, dep2_name]
                                                all_paths.append(path)
                                                logger.debug(f"    경로 추가 (2단계까지만, 예외: {e}): {' > '.join(path)}")
                                                
                                        except Exception as e:
                                            logger.debug(f"  2단계 처리 중 오류: {e}")
                                            continue
                                else:
                                    # 정말 2단계가 없으면 1단계까지만
                                    path = [dep1_name]
                                    all_paths.append(path)
                                    logger.debug(f"  경로 추가 (1단계까지만): {' > '.join(path)}")
                            else:
                                # 정말 2단계가 없으면 1단계까지만
                                path = [dep1_name]
                                all_paths.append(path)
                                logger.debug(f"  경로 추가 (1단계까지만): {' > '.join(path)}")
                        except Exception as e:
                            logger.debug(f"  JavaScript 강제 표시 실패: {e}")
                            # 정말 2단계가 없으면 1단계까지만
                            path = [dep1_name]
                            all_paths.append(path)
                            logger.debug(f"  경로 추가 (1단계까지만): {' > '.join(path)}")
                        
                except Exception as e:
                    # 2단계 찾기 실패, 1단계까지만
                    logger.debug(f"  2단계 찾기 실패: {e}, 1단계까지만 추가")
                    path = [dep1_name]
                    all_paths.append(path)
                    logger.debug(f"  경로 추가 (1단계까지만): {' > '.join(path)}")
                
                # 다음 1단계로 넘어가기 전에 메뉴 다시 열기
                if i < len(dep1_links):
                    # 메뉴가 닫혔을 수 있으니 다시 열기
                    if not open_ssadagu_menu(driver):
                        logger.warning("메뉴 재오픈 실패, 계속 진행...")
                        time.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"1단계 처리 중 오류: {e}")
                continue
        
        logger.info(f"총 {len(all_paths)}개 카테고리 경로 발견")
        return all_paths
        
    except Exception as e:
        logger.error(f"카테고리 경로 찾기 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")


def print_category_paths(paths: List[List[str]]):
    """
    카테고리 경로를 보기 좋게 출력
    """
    print("\n" + "=" * 80)
    print(f"발견된 카테고리 경로: {len(paths)}개")
    print("=" * 80)
    
    # 1단계별로 그룹화
    by_level1 = {}
    for path in paths:
        level1 = path[0] if path else "알 수 없음"
        if level1 not in by_level1:
            by_level1[level1] = []
        by_level1[level1].append(path)
    
    for level1, sub_paths in sorted(by_level1.items()):
        print(f"\n[{level1}] ({len(sub_paths)}개 경로)")
        for path in sub_paths:
            print(f"  {' > '.join(path)}")
    
    print("\n" + "=" * 80)
    print(f"총 {len(paths)}개 카테고리 경로")
    print("=" * 80)

