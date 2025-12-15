"""
싸다구 크롤러 메인 모듈
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
from ssadagu_parser.config import SCROLL_PAUSE_TIME, MAX_SCROLL_ATTEMPTS, BASE_URL, SSADAGU_SELECTORS
from ssadagu_parser.product_extractor import extract_products_from_html


def open_ssadagu_menu(driver: webdriver.Chrome) -> bool:
    """
    싸다구 전용 카테고리 메뉴 열기 함수
    
    Args:
        driver: Selenium WebDriver
        
    Returns:
        메뉴가 성공적으로 열렸는지 여부
    """
    # 1. 전체카테고리 아이콘 요소 찾기 (i.fa-bars 사용)
    try:
        trigger = driver.find_element(By.CSS_SELECTOR, "div.all_cate i.fa-bars")
    except:
        # .ico 선택자도 시도
        try:
            trigger = driver.find_element(By.CSS_SELECTOR, "div.all_cate .ico")
        except:
            # fallback: span.allc_bt
            trigger = driver.find_element(By.CSS_SELECTOR, "span.allc_bt")
    
    # 2. 아이콘을 화면 중앙에 위치시키기
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", trigger
    )
    time.sleep(0.5)
    
    # 3. 정확한 위치에 hover
    ActionChains(driver).move_to_element(trigger).perform()
    time.sleep(0.7)
    
    # 4. 메뉴 컨테이너 찾기
    try:
        menu = driver.find_element(By.CSS_SELECTOR, "div.all_cate .con_bx")
    except:
        menu = driver.find_element(By.CSS_SELECTOR, ".con_bx")
    
    # 5. visibility 로 확인해야 함 (싸다구는 display 안씀)
    visible = driver.execute_script(
        "return window.getComputedStyle(arguments[0]).visibility;", 
        menu
    )
    
    if visible == "visible":
        logger.info("메뉴 열림 성공")
        # 메뉴가 열리면 즉시 메뉴 내부로 커서 이동 (메뉴 유지)
        ActionChains(driver).move_to_element(menu).perform()
        time.sleep(0.3)
        return True
    else:
        logger.warning(f"메뉴가 열리지 않음 (visibility: {visible})")
        return False


def navigate_to_category(driver: webdriver.Chrome, category_path: list) -> Optional[str]:
    """
    메인 페이지에서 중첩된 카테고리로 이동 (hover 기반)
    
    Args:
        driver: Selenium WebDriver
        category_path: 카테고리 경로 리스트 (예: ["패션의류/이너웨어", "남성의류", "셔츠"])
        
    Returns:
        카테고리 페이지 URL 또는 None (실패 시)
    """
    try:
        logger.info(f"메인 페이지 접속: {BASE_URL}")
        driver.get(BASE_URL)
        time.sleep(2)  # 페이지 로드 대기
        
        # 전체카테고리 메뉴 열기 (싸다구 전용 함수 사용)
        logger.info("전체카테고리 메뉴 열기...")
        
        # 체크포인트: 아이콘 요소가 로드될 때까지 대기 (여러 선택자 시도)
        trigger = None
        selectors = [
            "div.all_cate i.fa-bars",
            "div.all_cate .ico",
            "span.allc_bt",
        ]
        
        for selector in selectors:
            try:
                trigger = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.info(f"전체카테고리 아이콘 요소 발견: {selector}")
                break
            except:
                continue
        
        if not trigger:
            logger.error("전체카테고리 아이콘 요소를 찾을 수 없습니다")
            return None
        
        # 메뉴 열기
        menu_opened = open_ssadagu_menu(driver)
        if not menu_opened:
            logger.error("싸다구 메뉴 open 실패")
            return None
        
        # 카테고리 경로를 따라가기
        action_chains = ActionChains(driver)
        current_submenu = None  # 현재 열린 하위 메뉴 컨테이너
        
        for i, category_name in enumerate(category_path):
            logger.info(f"{i+1}단계: '{category_name}' 찾는 중...")
            
            # 현재 레벨의 카테고리 링크 찾기
            # dep_1, dep_2, dep_3 등으로 구분
            if i == 0:
                # 1단계: dep_1 (전체 메뉴에서 찾기)
                selector = "ul.dep_1cover.link_cover > li.dep_1 > a.cate_tit"
                search_container = driver  # 전체 페이지에서 검색
            elif i == 1:
                # 2단계: dep_2 (열린 하위 메뉴 내부에서 찾기)
                # current_submenu가 설정되어 있어야 함 (1단계 hover 후 설정됨)
                if current_submenu:
                    selector = "li.dep_2 > a.cate_tit"
                    search_container = current_submenu  # 하위 메뉴 내부에서만 검색
                else:
                    # current_submenu가 없으면 에러 (이론적으로는 발생하지 않아야 함)
                    logger.error("2단계 카테고리를 찾기 전에 1단계 hover가 완료되지 않았습니다")
                    return None
            elif i == 2:
                # 3단계: dep_3 (열린 하위 메뉴 내부에서 찾기)
                # current_submenu가 설정되어 있어야 함 (2단계 hover 후 설정됨)
                if current_submenu:
                    selector = "li.dep_3 > a.cate_tit"
                    search_container = current_submenu  # 하위 메뉴 내부에서만 검색
                else:
                    # current_submenu가 없으면 에러 (이론적으로는 발생하지 않아야 함)
                    logger.error("3단계 카테고리를 찾기 전에 2단계 hover가 완료되지 않았습니다")
                    return None
            else:
                logger.error(f"지원하지 않는 깊이: {i+1}단계")
                return None
            
            # 해당 레벨의 모든 링크 찾기 (컨테이너 내부에서)
            wait = WebDriverWait(driver, 5)
            if current_submenu and i > 0:
                # 하위 메뉴 내부에서 찾기
                links = current_submenu.find_elements(By.CSS_SELECTOR, selector)
            else:
                # 전체 페이지에서 찾기
                links = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
            
            target_link = None
            for link in links:
                link_text = link.text.strip()
                logger.debug(f"  발견된 카테고리: {link_text}")
                
                # 정확히 일치하거나 포함되는 경우
                if category_name in link_text or link_text == category_name:
                    target_link = link
                    logger.info(f"  카테고리 발견: {link_text}")
                    break
            
            if not target_link:
                logger.error(f"'{category_name}' 카테고리를 찾을 수 없습니다")
                # 찾은 카테고리 목록 출력
                found_categories = [link.text.strip() for link in links[:10]]
                logger.info(f"  찾은 카테고리 (상위 10개): {found_categories}")
                return None
            
            # 마지막 단계가 아니면 hover, 마지막이면 클릭
            if i < len(category_path) - 1:
                # 중간 단계: hover
                logger.info(f"  '{category_name}'에 hover...")
                
                # 요소를 화면 중앙에 위치
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", target_link
                )
                time.sleep(0.3)
                
                # hover 수행
                action_chains.move_to_element(target_link).perform()
                time.sleep(0.8)  # 하위 메뉴가 열릴 시간 대기
                
                # 하위 메뉴가 열렸는지 확인 (다음 단계의 메뉴 컨테이너 확인)
                next_level = i + 1
                if next_level == 1:
                    submenu_selector = "div.dep_2cover"
                    parent_class = "dep_1"
                elif next_level == 2:
                    submenu_selector = "div.dep_3cover"
                    parent_class = "dep_2"
                else:
                    submenu_selector = None
                    parent_class = None
                
                if submenu_selector and parent_class:
                    try:
                        # 중요: 현재 hover한 링크의 부모 li 내부에서만 하위 메뉴 찾기
                        target_link_parent = target_link.find_element(By.XPATH, f"./ancestor::li[contains(@class, '{parent_class}')]")
                        submenu = target_link_parent.find_element(By.CSS_SELECTOR, submenu_selector)
                        
                        # visibility, display, is_displayed 모두 체크
                        submenu_visible = driver.execute_script(
                            "return window.getComputedStyle(arguments[0]).visibility;",
                            submenu
                        )
                        submenu_display = driver.execute_script(
                            "return window.getComputedStyle(arguments[0]).display;",
                            submenu
                        )
                        submenu_is_displayed = submenu.is_displayed()
                        
                        if submenu_visible == "visible" and submenu_display != "none" and submenu_is_displayed:
                            logger.info(f"  하위 메뉴 열림 확인 (visibility: {submenu_visible}, display: {submenu_display}, is_displayed: {submenu_is_displayed})")
                            
                            # 중요: 하위 메뉴 내부로 커서를 빠르게 이동 (메뉴 유지)
                            # 하위 메뉴의 첫 번째 링크나 중앙으로 이동
                            try:
                                # 하위 메뉴 내부의 첫 번째 링크 찾기
                                first_link = submenu.find_element(By.CSS_SELECTOR, "a.cate_tit")
                                ActionChains(driver).move_to_element(first_link).perform()
                                logger.debug("  하위 메뉴 내부로 커서 이동 완료")
                            except:
                                # 링크를 찾을 수 없으면 하위 메뉴 자체로 이동
                                ActionChains(driver).move_to_element(submenu).perform()
                                logger.debug("  하위 메뉴 컨테이너로 커서 이동 완료")
                            
                            # 다음 단계에서 이 하위 메뉴 내부에서만 검색하도록 저장
                            current_submenu = submenu
                            time.sleep(0.3)
                        else:
                            logger.warning(f"  하위 메뉴가 열리지 않음 (visibility: {submenu_visible}, display: {submenu_display}, is_displayed: {submenu_is_displayed})")
                    except Exception as e:
                        logger.debug(f"  하위 메뉴 확인 실패: {e}")
            else:
                # 마지막 단계: 클릭
                logger.info(f"  '{category_name}' 클릭...")
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


def crawl_from_main(category_path: list, max_products: int = 100, driver: Optional[webdriver.Chrome] = None) -> List[Dict[str, str]]:
    """
    메인 페이지에서 시작하여 중첩된 카테고리로 이동 후 크롤링
    
    Args:
        category_path: 카테고리 경로 리스트 (예: ["패션의류/이너웨어", "남성의류", "셔츠"])
        max_products: 최대 수집할 상품 개수 (기본값: 100)
        driver: 기존 WebDriver 인스턴스 (전달 시 재사용, None이면 새로 생성)
        
    Returns:
        상품 정보 리스트
    """
    category_path_str = " > ".join(category_path)
    logger.info(f"메인 페이지에서 카테고리 경로 '{category_path_str}' 크롤링 시작")
    
    should_close_driver = False
    try:
        # 브라우저 설정 (전달되지 않았으면 새로 생성)
        if driver is None:
            driver = setup_browser(headless=False)
            should_close_driver = True
        
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
        # 이 함수에서 생성한 브라우저만 종료
        if should_close_driver and driver:
            driver.quit()
            logger.info("브라우저 종료")


def crawl_category(category_url: str, max_products: int = 100) -> List[Dict[str, str]]:
    """
    카테고리 URL에서 상품 정보 크롤링
    
    Args:
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수 (기본값: 100)
        
    Returns:
        상품 정보 리스트
    """
    logger.info(f"카테고리 크롤링 시작: {category_url}")
    
    driver = None
    try:
        # 브라우저 설정
        driver = setup_browser(headless=False)
        driver.get(category_url)
        
        return _crawl_category_page(driver, category_url, max_products)
        
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")


def _crawl_category_page(driver: webdriver.Chrome, category_url: str, max_products: int) -> List[Dict[str, str]]:
    """
    카테고리 페이지에서 상품 크롤링 (내부 함수)
    
    Args:
        driver: Selenium WebDriver
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수
        
    Returns:
        상품 정보 리스트
    """
    try:
        # 페이지 로드 대기
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_info")))
        
        logger.info("페이지 로드 완료")
        
        all_products = []
        scroll_attempts = 0
        
        # 무한 스크롤 처리
        while len(all_products) < max_products and scroll_attempts < MAX_SCROLL_ATTEMPTS:
            # 현재 페이지의 HTML 가져오기
            html = driver.page_source
            
            # 상품 정보 추출
            products = extract_products_from_html(html)
            
            # 중복 제거 (product_id 기준)
            existing_ids = {p.get("product_id") for p in all_products if p.get("product_id")}
            new_products = [
                p for p in products 
                if not p.get("product_id") or p.get("product_id") not in existing_ids
            ]
            
            all_products.extend(new_products)
            logger.info(f"현재 수집된 상품: {len(all_products)}개")
            
            # 최대 개수 도달 시 종료
            if len(all_products) >= max_products:
                break
            
            # 더 로드할 상품이 있는지 확인
            if not scroll_to_load_more(driver):
                logger.info("더 이상 로드할 상품이 없습니다")
                break
            
            scroll_attempts += 1
        
        # 최대 개수만큼만 반환
        result = all_products[:max_products]
        logger.info(f"크롤링 완료: {len(result)}개 상품 수집")
        
        return result
        
    except TimeoutException:
        logger.error("페이지 로드 타임아웃")
        return []
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    """
    카테고리 URL에서 상품 정보 크롤링
    
    Args:
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수 (기본값: 100)
        
    Returns:
        상품 정보 리스트
    """
    logger.info(f"카테고리 크롤링 시작: {category_url}")
    
    driver = None
    try:
        # 브라우저 설정
        driver = setup_browser(headless=False)
        driver.get(category_url)
        
        # 페이지 로드 대기
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_info")))
        
        logger.info("페이지 로드 완료")
        
        all_products = []
        scroll_attempts = 0
        
        # 무한 스크롤 처리
        while len(all_products) < max_products and scroll_attempts < MAX_SCROLL_ATTEMPTS:
            # 현재 페이지의 HTML 가져오기
            html = driver.page_source
            
            # 상품 정보 추출
            products = extract_products_from_html(html)
            
            # 중복 제거 (product_id 기준)
            existing_ids = {p.get("product_id") for p in all_products if p.get("product_id")}
            new_products = [
                p for p in products 
                if not p.get("product_id") or p.get("product_id") not in existing_ids
            ]
            
            all_products.extend(new_products)
            logger.info(f"현재 수집된 상품: {len(all_products)}개")
            
            # 최대 개수 도달 시 종료
            if len(all_products) >= max_products:
                break
            
            # 더 로드할 상품이 있는지 확인
            if not scroll_to_load_more(driver):
                logger.info("더 이상 로드할 상품이 없습니다")
                break
            
            scroll_attempts += 1
        
        # 최대 개수만큼만 반환
        result = all_products[:max_products]
        logger.info(f"크롤링 완료: {len(result)}개 상품 수집")
        
        return result
        
    except TimeoutException:
        logger.error("페이지 로드 타임아웃")
        return []
    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")

