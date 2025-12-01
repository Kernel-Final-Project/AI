"""
무신사 사이트의 모든 카테고리 경로를 찾는 모듈
"""
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from musinsa_parser.crawler import open_musinsa_menu
from musinsa_parser.config import BASE_URL, MUSINSA_SELECTORS


def find_all_category_paths() -> List[List[str]]:
    """
    무신사 사이트의 모든 카테고리 경로를 찾아서 반환
    
    Returns:
        카테고리 경로 리스트의 리스트
        예: [
            ["뷰티", "스킨케어"],
            ["뷰티", "마스크팩"],
            ...
        ]
    """
    logger.info("모든 카테고리 경로 찾기 시작")
    
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 카테고리 메뉴 열기
        if not open_musinsa_menu(driver):
            logger.error("메뉴 열기 실패")
            return []
        
        logger.info("메뉴 열림, 카테고리 경로 탐색 시작...")
        
        # 모달 찾기
        try:
            modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        except Exception as e:
            logger.error(f"카테고리 모달을 찾을 수 없습니다: {e}")
            return []
        
        all_paths = []
        
        # ===== 무신사 모달 구조: 왼쪽 메인 카테고리 목록 =====
        # 왼쪽 메인 카테고리는 MainMenu__StyledContainer 안의 MainMenuRow__Container 요소들
        # 각 요소는 data-category-name 속성에 카테고리 이름을 가지고 있음
        
        try:
            # 왼쪽 메인 카테고리 컨테이너 찾기
            main_menu_container = modal.find_element(By.CSS_SELECTOR, "div.MainMenu__StyledContainer-sc-1v9l62g-0")
            
            # 각 메인 카테고리 요소 찾기
            main_menu_rows = main_menu_container.find_elements(By.CSS_SELECTOR, "p.MainMenuRow__Container-sc-ck8m2r-0")
            logger.info(f"왼쪽 메인 카테고리 요소: {len(main_menu_rows)}개 발견")
            
            # 각 메인 카테고리 이름 추출
            for i, row in enumerate(main_menu_rows, 1):
                try:
                    # 방법 1: data-category-name 속성 사용
                    category_name = row.get_attribute('data-category-name')
                    
                    # 방법 2: 속성이 없으면 내부 텍스트 사용
                    if not category_name:
                        category_name = row.text.strip()
                    
                    if not category_name or category_name in ["전체", "남성", "여성"]:
                        continue
                    
                    logger.info(f"[메인 {i}/{len(main_menu_rows)}] {category_name}")
                    
                    # ===== 모든 메인 카테고리에 하위 카테고리 탐지 적용 =====
                    # 메인 카테고리 클릭하여 하위 카테고리 표시
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.3)
                    row.click()
                    time.sleep(0.8)  # 하위 카테고리 로드 대기
                    
                    # 업데이트된 모달에서 하위 카테고리 컨테이너 찾기
                    updated_modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
                    
                    try:
                        # 하위 카테고리 컨테이너 찾기 (공통 구조)
                        sub_body = updated_modal.find_element(By.CSS_SELECTOR, "div.CategorySubBody__StyledGroup-sc-ysyv1g-1")
                        
                        # 하위 카테고리 링크들 찾기 (공통 구조)
                        sub_items = sub_body.find_elements(By.CSS_SELECTOR, "a.CategorySubItem__StyledContainer-sc-1kgwyy5-0")
                        
                        if sub_items:
                            logger.info(f"  → 하위 카테고리 {len(sub_items)}개 발견")
                            
                            # 각 하위 카테고리 이름 추출
                            for sub_item in sub_items:
                                try:
                                    # span.CategorySubItem__StyledTitle에서 텍스트 추출 (공통 구조)
                                    sub_name_elem = sub_item.find_element(By.CSS_SELECTOR, "span.CategorySubItem__StyledTitle-sc-1kgwyy5-1")
                                    sub_name = sub_name_elem.text.strip()
                                    
                                    if sub_name:
                                        path = [category_name, sub_name]
                                        all_paths.append(path)
                                        logger.debug(f"    경로 추가: {' > '.join(path)}")
                                except Exception as e:
                                    logger.debug(f"    하위 카테고리 이름 추출 실패: {e}")
                                    continue
                        else:
                            # 하위 카테고리가 없으면 메인 카테고리만 추가
                            all_paths.append([category_name])
                                    
                    except Exception as e:
                        logger.debug(f"  하위 카테고리 컨테이너를 찾을 수 없습니다 (하위 없음 또는 오류): {e}")
                        # 하위 카테고리를 찾지 못해도 메인 카테고리는 추가
                        all_paths.append([category_name])
                    
                except Exception as e:
                    logger.debug(f"메인 카테고리 요소 처리 중 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"왼쪽 메인 카테고리 컨테이너를 찾을 수 없습니다: {e}")
            # 대체 방법: 기존 방식으로 시도
            logger.info("대체 방법으로 메인 카테고리 찾기 시도...")
            try:
                # CategorySubHeader 클래스를 가진 링크들 찾기
                header_links = modal.find_elements(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
                for link in header_links:
                    text = link.text.strip()
                    if text and text not in ["전체", "남성", "여성", "전체 보기"]:
                        all_paths.append([text])
            except:
                pass
        
        # ===== 원래 버전 (되돌리기용) =====
        # 주석 처리된 원래 코드 - 문제 발생 시 아래 주석을 해제하고 위 코드를 주석 처리
        """
        # 1단계 카테고리 찾기 (클래스로 구분)
        first_level_links = modal.find_elements(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
        logger.info(f"1단계 카테고리: {len(first_level_links)}개 발견")
        
        # 각 1단계 카테고리 처리
        for i, dep1_link in enumerate(first_level_links, 1):
            try:
                dep1_name = dep1_link.text.strip()
                if not dep1_name or dep1_name in ["전체", "남성", "여성"]:
                    continue
                
                logger.info(f"[1단계 {i}/{len(first_level_links)}] {dep1_name}")
                
                # 1단계 카테고리의 부모 컨테이너 찾기
                try:
                    dep1_parent = dep1_link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'CategorySubRow__StyledContainer')]")
                except:
                    logger.debug(f"  부모 컨테이너를 찾을 수 없습니다: {dep1_name}")
                    all_paths.append([dep1_name])
                    continue
                
                # 부모 컨테이너 내에서 2단계 카테고리 찾기
                dep2_links = dep1_parent.find_elements(By.CSS_SELECTOR, "a.CategorySubItem__StyledContainer-sc-1kgwyy5-0")
                
                dep2_categories = []
                for dep2_link in dep2_links:
                    dep2_text = dep2_link.text.strip()
                    if dep2_text and dep2_text != "전체 보기":
                        dep2_categories.append(dep2_text)
                
                if dep2_categories:
                    logger.info(f"  → 2단계 카테고리 {len(dep2_categories)}개 발견")
                    for dep2_name in dep2_categories:
                        path = [dep1_name, dep2_name]
                        all_paths.append(path)
                        logger.debug(f"    경로 추가: {' > '.join(path)}")
                else:
                    all_paths.append([dep1_name])
                    logger.debug(f"  경로 추가 (1단계까지만): {dep1_name}")
                
            except Exception as e:
                logger.debug(f"1단계 처리 중 오류: {e}")
                continue
        """
        
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
    for i, path in enumerate(paths, 1):
        path_str = " > ".join(path)
        print(f"{i:4d}. {path_str}")


if __name__ == "__main__":
    paths = find_all_category_paths()
    
    print("\n" + "=" * 80)
    print(f"총 {len(paths)}개 카테고리 경로 발견")
    print("=" * 80)
    print_category_paths(paths)

