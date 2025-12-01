"""
무신사 크롤러 메인 모듈
"""
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import time

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from parsers.musinsa.config import SCROLL_PAUSE_TIME, MAX_SCROLL_ATTEMPTS, BASE_URL, MUSINSA_SELECTORS
from parsers.musinsa.product_extractor import extract_products_from_html


def open_musinsa_menu(driver: webdriver.Chrome) -> bool:
    """
    무신사 전용 카테고리 메뉴 열기 함수
    
    Args:
        driver: Selenium WebDriver
        
    Returns:
        메뉴가 성공적으로 열렸는지 여부
    """
    try:
        # 1. 카테고리 아이콘 찾기
        wait = WebDriverWait(driver, 5)
        category_icon = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, MUSINSA_SELECTORS["category_icon"]))
        )
        
        # 2. 아이콘을 화면 중앙에 위치시키기
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", category_icon
        )
        time.sleep(0.3)
        
        # 3. 클릭
        category_icon.click()
        time.sleep(0.5)  # 메뉴 열림 대기
        
        # 4. 메뉴 모달이 열렸는지 확인 (opacity: 1)
        try:
            modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
            opacity = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).opacity;",
                modal
            )
            
            if float(opacity) >= 1.0:
                logger.info("메뉴 열림 성공")
                return True
            else:
                logger.warning(f"메뉴가 열리지 않음 (opacity: {opacity})")
                return False
        except NoSuchElementException:
            logger.warning("메뉴 모달을 찾을 수 없습니다")
            return False
            
    except TimeoutException:
        logger.error("카테고리 아이콘을 찾을 수 없습니다")
        return False
    except Exception as e:
        logger.error(f"메뉴 열기 중 오류: {e}")
        return False


def find_category_link(driver: webdriver.Chrome, category_name: str, search_container=None) -> Optional:
    """
    카테고리 링크 찾기 (텍스트 기반)
    
    Args:
        driver: Selenium WebDriver
        category_name: 찾을 카테고리 이름
        search_container: 검색할 컨테이너 (None이면 전체 페이지)
        
    Returns:
        WebElement 또는 None
    """
    if search_container is None:
        search_container = driver
    
    try:
        # 모든 링크 요소 찾기 (data-category-id가 있는 요소 우선)
        wait = WebDriverWait(search_container, 5)
        
        # 방법 1: data-category-id가 있는 링크 중에서 텍스트로 찾기
        links = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-category-id]"))
        )
        
        for link in links:
            link_text = link.text.strip()
            if link_text == category_name:
                logger.info(f"  카테고리 발견: {category_name}")
                return link
        
        # 방법 2: 일반 링크에서 텍스트로 찾기 (fallback)
        all_links = search_container.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            link_text = link.text.strip()
            if link_text == category_name:
                logger.info(f"  카테고리 발견 (fallback): {category_name}")
                return link
        
        logger.warning(f"카테고리 '{category_name}'를 찾을 수 없습니다")
        return None
        
    except TimeoutException:
        logger.warning(f"카테고리 '{category_name}'를 찾을 수 없습니다 (타임아웃)")
        return None
    except Exception as e:
        logger.error(f"카테고리 찾기 중 오류: {e}")
        return None


def navigate_to_category(driver: webdriver.Chrome, category_path: list) -> Optional[str]:
    """
    메인 페이지에서 중첩된 카테고리로 이동 (클릭 기반)
    
    Args:
        driver: Selenium WebDriver
        category_path: 카테고리 경로 리스트 (예: ["뷰티", "스킨케어"])
        
    Returns:
        카테고리 페이지 URL 또는 None (실패 시)
    """
    try:
        logger.info(f"메인 페이지 접속: {BASE_URL}")
        driver.get(BASE_URL)
        time.sleep(2)  # 페이지 로드 대기
        
        # 카테고리 메뉴 열기
        logger.info("카테고리 메뉴 열기...")
        menu_opened = open_musinsa_menu(driver)
        if not menu_opened:
            logger.error("무신사 메뉴 열기 실패")
            return None
        
        # 카테고리 경로를 따라가기
        # 모달 찾기
        try:
            current_modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        except NoSuchElementException:
            logger.error("카테고리 모달을 찾을 수 없습니다")
            return None
        
        # 무신사는 모달이 열리면 모든 카테고리가 동시에 표시될 수 있음
        # 1단계 카테고리에 hover하면 오른쪽에 2단계가 표시되거나,
        # 또는 모달 내에서 직접 모든 카테고리를 찾을 수 있음
        
        for i, category_name in enumerate(category_path):
            logger.info(f"{i+1}단계: '{category_name}' 찾는 중...")
            
            # 카테고리 링크 찾기 (모달 내에서)
            target_link = find_category_link(driver, category_name, current_modal)
            if not target_link:
                logger.error(f"카테고리 '{category_name}'를 찾을 수 없습니다")
                return None
            
            # 마지막 단계가 아니면 hover하여 하위 메뉴 표시
            if i < len(category_path) - 1:
                # 중간 단계: hover만 수행 (클릭하면 페이지로 이동하므로 hover만)
                logger.info(f"  '{category_name}'에 hover...")
                
                # 요소를 화면 중앙에 위치
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", target_link
                )
                time.sleep(0.3)
                
                # hover 수행
                action_chains = ActionChains(driver)
                action_chains.move_to_element(target_link).perform()
                time.sleep(0.8)  # 하위 메뉴가 표시될 시간 대기
                
                # 하위 메뉴가 표시되었는지 확인 (다음 단계 카테고리 찾기)
                next_category_name = category_path[i + 1]
                
                # 방법 1: 모달 내에서 직접 다음 단계 카테고리 찾기 (무신사는 모든 카테고리가 모달에 표시됨)
                all_links = current_modal.find_elements(By.TAG_NAME, "a")
                next_link = None
                for link in all_links:
                    if link.text.strip() == next_category_name:
                        next_link = link
                        logger.info(f"  하위 카테고리 발견: '{next_category_name}'")
                        break
                
                # 방법 2: hover 후 나타난 하위 메뉴에서 찾기 (방법 1이 실패한 경우)
                if not next_link:
                    try:
                        wait = WebDriverWait(current_modal, 2)
                        next_link = wait.until(
                            EC.presence_of_element_located((By.XPATH, f".//a[normalize-space(text())='{next_category_name}']"))
                        )
                        logger.info(f"  hover 후 하위 카테고리 발견: '{next_category_name}'")
                    except TimeoutException:
                        logger.warning(f"  하위 카테고리 '{next_category_name}'를 찾을 수 없습니다")
                
                if next_link:
                    # 하위 메뉴 내부로 커서 이동 (메뉴 유지)
                    action_chains.move_to_element(next_link).perform()
                    time.sleep(0.3)
                else:
                    logger.error(f"  하위 카테고리 '{next_category_name}'를 찾을 수 없습니다")
                    return None
            else:
                # 마지막 단계: 클릭하여 페이지 이동
                logger.info(f"  '{category_name}' 클릭 (페이지 이동)...")
                category_url = target_link.get_attribute('href')
                
                if not category_url:
                    logger.error("카테고리 URL을 찾을 수 없습니다")
                    return None
                
                # URL로 직접 이동 (클릭 대신)
                logger.info(f"카테고리 페이지로 이동: {category_url}")
                driver.get(category_url)
                time.sleep(2)  # 페이지 로드 대기
                
                return category_url
        
        return None
        
    except TimeoutException as e:
        logger.error(f"카테고리 메뉴를 찾을 수 없습니다 (타임아웃): {e}")
        return None
    except Exception as e:
        logger.error(f"카테고리 이동 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def scroll_to_load_more(driver: webdriver.Chrome) -> bool:
    """
    무한 스크롤 처리 - 페이지 끝까지 스크롤하여 더 많은 상품 로드
    
    Args:
        driver: Selenium WebDriver
        
    Returns:
        더 로드할 상품이 있는지 여부
    """
    # 현재 페이지 높이
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # 페이지 끝으로 스크롤
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # 새 콘텐츠 로드 대기
    time.sleep(SCROLL_PAUSE_TIME)
    
    # 새로운 페이지 높이
    new_height = driver.execute_script("return document.body.scrollHeight")
    
    # 높이가 변하지 않으면 더 이상 로드할 상품 없음
    return new_height != last_height


def _crawl_category_page(driver: webdriver.Chrome, category_url: str, max_products: int = 100) -> List[Dict[str, str]]:
    """
    카테고리 페이지에서 상품 정보 크롤링 (내부 함수)
    
    Args:
        driver: Selenium WebDriver
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수
        
    Returns:
        상품 정보 리스트
    """
    try:
        logger.info(f"카테고리 페이지 크롤링 시작: {category_url}")
        
        all_products = []
        scroll_attempts = 0
        
        # 무한 스크롤로 상품 로드
        while len(all_products) < max_products and scroll_attempts < MAX_SCROLL_ATTEMPTS:
            # 현재 페이지의 HTML 가져오기
            html = driver.page_source
            
            # 상품 정보 추출
            products = extract_products_from_html(html)
            
            # 중복 제거 (product_id 기준)
            existing_ids = {p.get("product_id") for p in all_products if p.get("product_id")}
            new_products = [p for p in products if p.get("product_id") not in existing_ids]
            
            all_products.extend(new_products)
            
            logger.info(f"현재 수집된 상품: {len(all_products)}개 (목표: {max_products}개)")
            
            # 목표 개수에 도달했으면 종료
            if len(all_products) >= max_products:
                break
            
            # 더 많은 상품 로드 시도
            if not scroll_to_load_more(driver):
                logger.info("더 이상 로드할 상품이 없습니다")
                break
            
            scroll_attempts += 1
        
        # 최대 개수만큼만 반환
        result = all_products[:max_products]
        logger.info(f"크롤링 완료: {len(result)}개 상품 수집")
        
        return result
        
    except Exception as e:
        logger.error(f"카테고리 페이지 크롤링 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def crawl_from_main(category_path: list, max_products: int = 100) -> List[Dict[str, str]]:
    """
    메인 페이지에서 시작하여 중첩된 카테고리로 이동 후 크롤링
    
    Args:
        category_path: 카테고리 경로 리스트 (예: ["뷰티", "스킨케어"])
        max_products: 최대 수집할 상품 개수 (기본값: 100)
        
    Returns:
        상품 정보 리스트
    """
    category_path_str = " > ".join(category_path)
    logger.info(f"메인 페이지에서 카테고리 경로 '{category_path_str}' 크롤링 시작")
    
    driver = None
    try:
        # 브라우저 설정
        driver = setup_browser(headless=False)
        
        # 메인 페이지에서 카테고리로 이동
        category_url = navigate_to_category(driver, category_path)
        
        if not category_url:
            logger.error("카테고리로 이동 실패")
            return []
        
        # 카테고리 페이지 크롤링
        return _crawl_category_page(driver, category_url, max_products)
        
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")


def crawl_category(category_url: str, max_products: int = 100) -> List[Dict[str, str]]:
    """
    카테고리 URL에서 상품 정보 크롤링
    
    Args:
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수
        
    Returns:
        상품 정보 리스트
    """
    logger.info(f"카테고리 URL에서 크롤링 시작: {category_url}")
    
    driver = None
    try:
        # 브라우저 설정
        driver = setup_browser(headless=False)
        
        # 카테고리 페이지 접속
        driver.get(category_url)
        time.sleep(2)  # 페이지 로드 대기
        
        # 카테고리 페이지 크롤링
        return _crawl_category_page(driver, category_url, max_products)
        
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")

