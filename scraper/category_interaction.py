"""
카테고리 메뉴와의 동적 상호작용 모듈
Selenium을 사용하여 hover, 클릭 등의 동작을 수행합니다.
"""
from typing import Optional
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from bs4 import Tag
import time

from utils.logger import logger
from utils.category_patterns import SUBMENU_SELECTORS


def find_selenium_element(
    driver: webdriver.Chrome,
    bs4_tag: Tag,
    timeout: float = 3.0
) -> Optional[WebElement]:
    """
    BeautifulSoup Tag를 Selenium WebElement로 변환
    
    Args:
        driver: Selenium WebDriver
        bs4_tag: BeautifulSoup Tag 객체
        timeout: 요소 찾기 타임아웃 (초)
        
    Returns:
        찾은 WebElement 또는 None
    """
    tag_name = bs4_tag.name
    classes = bs4_tag.get("class", [])
    element_id = bs4_tag.get("id", "")
    text = bs4_tag.get_text(strip=True)
    
    # 1. ID로 찾기 (가장 정확)
    if element_id:
        try:
            element = driver.find_element(By.ID, element_id)
            logger.debug(f"요소 찾기 성공 (ID): {element_id}")
            return element
        except NoSuchElementException:
            pass
    
    # 2. XPath 사용 (더 정확한 매칭)
    # 텍스트가 있으면 텍스트로 찾기
    if text and len(text) > 0 and len(text) < 100:
        # XPath 텍스트 이스케이프 처리 (작은따옴표 제거)
        text_escaped = text[:30].replace("'", "").replace('"', '')
        if text_escaped:
            try:
                xpath = f"//{tag_name}[contains(text(), '{text_escaped}')]"
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    logger.debug(f"요소 찾기 성공 (XPath + 텍스트): {text_escaped}")
                    return elements[0]
            except:
                pass
    
    # 3. Class 조합으로 찾기
    if classes:
        # 모든 클래스 조합 시도
        for i in range(len(classes), 0, -1):
            class_selector = "." + ".".join(classes[:i])
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, class_selector)
                if elements:
                    # 텍스트로 필터링 (가능하면)
                    if text and len(text) > 0:
                        for elem in elements:
                            try:
                                if text[:30] in elem.text:
                                    logger.debug(f"요소 찾기 성공 (Class + 텍스트): {class_selector}")
                                    return elem
                            except:
                                pass
                    # 텍스트 매칭 실패하면 첫 번째 요소 반환
                    logger.debug(f"요소 찾기 성공 (Class): {class_selector}")
                    return elements[0]
            except:
                continue
    
    # 4. data-* 속성으로 찾기
    for attr_name, attr_value in bs4_tag.attrs.items():
        if attr_name.startswith("data-") and isinstance(attr_value, str):
            try:
                selector = f"[{attr_name}='{attr_value}']"
                element = driver.find_element(By.CSS_SELECTOR, selector)
                logger.debug(f"요소 찾기 성공 (data 속성): {selector}")
                return element
            except:
                pass
    
    # 5. aria-* 속성으로 찾기
    for attr_name, attr_value in bs4_tag.attrs.items():
        if attr_name.startswith("aria-") and isinstance(attr_value, str):
            try:
                selector = f"[{attr_name}='{attr_value}']"
                element = driver.find_element(By.CSS_SELECTOR, selector)
                logger.debug(f"요소 찾기 성공 (aria 속성): {selector}")
                return element
            except:
                pass
    
    # 6. 태그 + 텍스트 조합 (마지막 시도)
    if text and len(text) > 0:
        try:
            elements = driver.find_elements(By.TAG_NAME, tag_name)
            for elem in elements:
                try:
                    if text[:30] in elem.text:
                        logger.debug(f"요소 찾기 성공 (태그 + 텍스트): {tag_name}")
                        return elem
                except:
                    continue
        except:
            pass
    
    logger.warning(f"요소를 찾지 못했습니다 (태그: {tag_name}, 클래스: {classes[:2] if classes else None})")
    return None


def scroll_to_element(driver: webdriver.Chrome, element: WebElement) -> bool:
    """
    요소가 보이도록 스크롤
    
    Args:
        driver: Selenium WebDriver
        element: 스크롤할 WebElement
        
    Returns:
        스크롤 성공 여부 (bool)
    """
    try:
        # JavaScript로 요소를 뷰포트로 스크롤
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.3)  # 스크롤 애니메이션 대기
        logger.debug("요소로 스크롤 완료")
        return True
    except Exception as e:
        logger.warning(f"스크롤 실패: {e}")
        return False


def hover_element(
    driver: webdriver.Chrome, 
    element: WebElement, 
    wait_seconds: float = 0.5,
    scroll_to_element_first: bool = True
) -> bool:
    """
    특정 요소에 hover 동작 수행
    
    Args:
        driver: Selenium WebDriver
        element: hover할 WebElement
        wait_seconds: hover 후 대기 시간 (초)
        scroll_to_element_first: hover 전에 요소로 스크롤할지 여부
        
    Returns:
        hover 성공 여부 (bool)
    """
    try:
        # 요소가 상호작용 가능한지 체크
        if not element.is_displayed():
            logger.warning("요소가 화면에 보이지 않습니다. 스크롤 시도...")
            if scroll_to_element_first:
                scroll_to_element(driver, element)
                time.sleep(0.2)
            else:
                logger.error("요소가 보이지 않아 hover 불가")
                return False
        
        # 요소 크기 체크
        try:
            size = element.size
            if size['width'] == 0 or size['height'] == 0:
                logger.warning("요소 크기가 0입니다. 부모 요소로 대체 시도...")
                # 부모 요소로 대체 시도
                try:
                    parent = element.find_element(By.XPATH, "..")
                    if parent.is_displayed() and parent.size['width'] > 0 and parent.size['height'] > 0:
                        element = parent
                        logger.debug("부모 요소로 대체 성공")
                    else:
                        logger.error("부모 요소도 상호작용 불가")
                        return False
                except:
                    logger.error("부모 요소 찾기 실패")
                    return False
        except:
            pass
        
        # 요소가 활성화되어 있는지 체크
        if not element.is_enabled():
            logger.warning("요소가 비활성화되어 있습니다")
        
        # 스크롤 (필요시)
        if scroll_to_element_first:
            scroll_to_element(driver, element)
        
        # hover 수행
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        
        # submenu 로딩을 위한 짧은 대기
        time.sleep(wait_seconds)
        
        logger.debug(f"hover 성공: {element.tag_name}")
        return True
        
    except WebDriverException as e:
        error_msg = str(e)
        if "element not interactable" in error_msg.lower():
            logger.warning("요소가 상호작용 불가능합니다. 스크롤 후 재시도...")
            try:
                scroll_to_element(driver, element)
                time.sleep(0.3)
                actions = ActionChains(driver)
                actions.move_to_element(element).perform()
                time.sleep(wait_seconds)
                logger.debug("스크롤 후 hover 성공")
                return True
            except:
                logger.error(f"스크롤 후 hover도 실패: {e}")
                return False
        else:
            logger.error(f"hover 실패 (WebDriverException): {e}")
            return False
    except Exception as e:
        logger.error(f"hover 중 예상치 못한 오류: {e}")
        return False


def hover_and_wait_for_submenu(
    driver: webdriver.Chrome,
    element: WebElement,
    timeout: float = 3.0,
    submenu_selectors: Optional[list] = None
) -> bool:
    """
    hover + submenu 로딩 대기
    
    Args:
        driver: Selenium WebDriver
        element: hover할 WebElement
        timeout: submenu 대기 타임아웃 (초)
        submenu_selectors: 커스텀 submenu CSS 선택자 리스트 (선택사항)
        
    Returns:
        hover 및 submenu 감지 성공 여부 (bool)
    """
    # hover 수행
    hover_success = hover_element(driver, element)
    if not hover_success:
        logger.warning("hover 실패로 인해 submenu 대기 중단")
        return False
    
    # submenu 선택자 설정
    if submenu_selectors is None:
        submenu_selectors = SUBMENU_SELECTORS
    
    try:
        # 1. 요소 내부에서 submenu 찾기 (우선 시도)
        try:
            for selector in submenu_selectors:
                try:
                    # 자식 요소 중 submenu 찾기
                    submenu = element.find_element(By.CSS_SELECTOR, selector)
                    # visibility 체크 (display:none이 아닌 실제 보이는지)
                    if submenu:
                        # JavaScript로 실제 visibility 확인
                        is_visible = driver.execute_script(
                            "return arguments[0].offsetParent !== null && "
                            "window.getComputedStyle(arguments[0]).display !== 'none' && "
                            "window.getComputedStyle(arguments[0]).visibility !== 'hidden';",
                            submenu
                        )
                        if is_visible:
                            logger.debug(f"submenu 감지 성공 (요소 내부, visible): {selector}")
                            return True
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"요소 내부 submenu 검색 중 오류 (무시): {e}")
                    continue
        except Exception as e:
            logger.debug(f"요소 내부 submenu 검색 중 오류 (무시): {e}")
        
        # 2. 전체 페이지에서 submenu 찾기
        for selector in submenu_selectors:
            try:
                # presence 체크
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                # visibility 체크
                submenu = driver.find_element(By.CSS_SELECTOR, selector)
                is_visible = driver.execute_script(
                    "return arguments[0].offsetParent !== null && "
                    "window.getComputedStyle(arguments[0]).display !== 'none' && "
                    "window.getComputedStyle(arguments[0]).visibility !== 'hidden';",
                    submenu
                )
                if is_visible:
                    logger.debug(f"submenu 감지 성공 (전체 페이지, visible): {selector}")
                    return True
            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"submenu 검색 중 오류 (무시): {e}")
                continue
        
        # 3. hover 후 DOM 변화 감지 (대안)
        try:
            # hover 전 요소 개수
            before_count = len(driver.find_elements(By.CSS_SELECTOR, "ul, div[class*='menu'], div[class*='submenu']"))
            
            # 잠시 대기 (submenu가 나타날 시간)
            time.sleep(0.5)
            
            # hover 후 요소 개수
            after_count = len(driver.find_elements(By.CSS_SELECTOR, "ul, div[class*='menu'], div[class*='submenu']"))
            
            if after_count > before_count:
                logger.debug("submenu 감지 성공 (DOM 변화 감지)")
                return True
        except Exception as e:
            logger.debug(f"DOM 변화 감지 중 오류 (무시): {e}")
        
        logger.warning("submenu를 찾지 못했습니다")
        return False
        
    except Exception as e:
        logger.error(f"submenu 대기 중 오류: {e}")
        return False


def click_element(
    driver: webdriver.Chrome,
    bs4_tag: Tag,
    wait_seconds: float = 1.0,
    use_js_fallback: bool = True
) -> tuple[bool, str]:
    """
    BeautifulSoup 태그를 Selenium WebElement로 변환 후 클릭 수행
    
    Args:
        driver: Selenium WebDriver
        bs4_tag: BeautifulSoup Tag 객체
        wait_seconds: 클릭 후 대기 시간 (초)
        use_js_fallback: 일반 클릭 실패 시 JS 클릭 시도 여부
        
    Returns:
        (성공 여부, 방법) 튜플
        - (True, "normal_click") - 일반 클릭 성공
        - (True, "js_click") - JS 클릭 성공
        - (True, "actionchains_click") - ActionChains 클릭 성공
        - (False, "selenium_element_not_found") - 요소 찾기 실패
        - (False, "click_failed: {error}") - 모든 클릭 방법 실패
    """
    # BeautifulSoup Tag → Selenium WebElement 변환
    selenium_elem = find_selenium_element(driver, bs4_tag)
    if selenium_elem is None:
        logger.warning("Selenium 요소를 찾지 못했습니다")
        return False, "selenium_element_not_found"
    
    try:
        # 요소 상호작용 가능 여부 체크
        if not selenium_elem.is_displayed():
            logger.warning("요소가 화면에 보이지 않습니다. 스크롤 시도...")
            scroll_to_element(driver, selenium_elem)
            time.sleep(0.2)
        
        # 요소 크기 체크
        try:
            size = selenium_elem.size
            if size['width'] == 0 or size['height'] == 0:
                logger.warning("요소 크기가 0입니다. 부모 요소로 대체 시도...")
                # 부모 요소로 대체 시도
                try:
                    parent = selenium_elem.find_element(By.XPATH, "..")
                    if parent.is_displayed() and parent.size['width'] > 0 and parent.size['height'] > 0:
                        selenium_elem = parent
                        logger.debug("부모 요소로 대체 성공")
                    else:
                        logger.error("부모 요소도 상호작용 불가")
                        return False, "click_failed: element_size_zero"
                except Exception as e:
                    logger.error(f"부모 요소 찾기 실패: {e}")
                    return False, f"click_failed: parent_not_found"
        except Exception as e:
            logger.debug(f"요소 크기 체크 중 오류 (무시): {e}")
        
        # 요소가 활성화되어 있는지 체크
        if not selenium_elem.is_enabled():
            logger.warning("요소가 비활성화되어 있습니다")
        
        # 스크롤 (기존 함수 사용)
        scroll_to_element(driver, selenium_elem)
        time.sleep(0.2)
        
        # 클릭 시도 1: 일반 클릭
        try:
            selenium_elem.click()
            time.sleep(wait_seconds)
            logger.debug("일반 클릭 성공")
            return True, "normal_click"
        except WebDriverException as e:
            error_msg = str(e).lower()
            if "element not interactable" in error_msg or "not clickable" in error_msg:
                logger.warning(f"일반 클릭 실패, 대안 방법 시도... ({e})")
            else:
                logger.warning(f"일반 클릭 실패: {e}")
        
        # 클릭 시도 2: ActionChains 클릭 (일부 경우 더 안정적)
        try:
            actions = ActionChains(driver)
            actions.click(selenium_elem).perform()
            time.sleep(wait_seconds)
            logger.debug("ActionChains 클릭 성공")
            return True, "actionchains_click"
        except WebDriverException as e:
            logger.debug(f"ActionChains 클릭 실패: {e}")
        except Exception as e:
            logger.debug(f"ActionChains 클릭 중 예상치 못한 오류: {e}")
        
        # 클릭 시도 3: JavaScript 강제 클릭 (fallback)
        if use_js_fallback:
            try:
                driver.execute_script("arguments[0].click();", selenium_elem)
                time.sleep(wait_seconds)
                logger.debug("JavaScript 클릭 성공")
                return True, "js_click"
            except Exception as e2:
                logger.error(f"JavaScript 클릭도 실패: {e2}")
                return False, f"click_failed: {e2}"
        else:
            return False, "click_failed: all_methods_failed"
            
    except WebDriverException as e:
        logger.error(f"클릭 중 WebDriverException: {e}")
        return False, f"click_failed: {e}"
    except Exception as e:
        logger.error(f"클릭 중 예상치 못한 오류: {e}")
        return False, f"click_failed: {e}"


# 이벤트 배너 처리 함수들은 html_extractor.py로 이동되었습니다
# 필요시 다음처럼 import하여 사용하세요:
# from scraper.html_extractor import handle_event_banner_and_navigate_to_main

def _detect_event_banner_deprecated(driver: webdriver.Chrome) -> bool:
    """
    이벤트 배너/팝업이 있는지 감지
    
    Args:
        driver: Selenium WebDriver
        
    Returns:
        이벤트 배너가 감지되었는지 여부 (bool)
    """
    try:
        current_url = driver.current_url.lower()
        
        # URL 패턴으로 이벤트 페이지 감지
        event_keywords = [
            'campaign', 'event', 'promotion', 'sale', 
            'popup', 'modal', 'banner', 'mujinjang'
        ]
        
        if any(keyword in current_url for keyword in event_keywords):
            logger.info(f"이벤트 페이지 감지: {current_url}")
            return True
        
        # 페이지 소스에서 이벤트 관련 키워드 확인
        page_source = driver.page_source.lower()
        event_text_keywords = [
            '이벤트', 'event', 'campaign', '프로모션',
            '특가', '세일', 'sale', '할인'
        ]
        
        # 닫기 버튼이 있는지 확인 (팝업/모달 존재 가능성)
        close_selectors = [
            "//button[contains(@class, 'close')]",
            "//button[contains(@class, 'CloseButton')]",
            "//button[contains(@aria-label, '닫기')]",
            "//button[contains(@aria-label, 'close')]",
            "//button[contains(text(), '닫기')]",
            "//button[contains(text(), 'X')]",
            "//*[contains(@class, 'close') and contains(@class, 'button')]",
            "//*[@aria-label='닫기' or @aria-label='close']"
        ]
        
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        logger.debug(f"닫기 버튼 발견: {selector}")
                        return True
            except:
                continue
        
        return False
        
    except Exception as e:
        logger.warning(f"이벤트 배너 감지 중 오류: {e}")
        return False


def _close_event_banner_deprecated(driver: webdriver.Chrome, timeout: float = 5.0) -> bool:
    """
    이벤트 배너/팝업 닫기 버튼 찾아서 클릭
    
    Args:
        driver: Selenium WebDriver
        timeout: 닫기 버튼 찾기 타임아웃 (초)
        
    Returns:
        닫기 성공 여부 (bool)
    """
    try:
        # 다양한 닫기 버튼 선택자 시도
        close_selectors = [
            # 무신사 특화 (우선 시도)
            "//*[contains(@class, 'LocalAppBar__CloseButton')]",
            "//div[contains(@class, 'LocalAppBar__CloseButton')]",
            "//button[contains(@class, 'LocalAppBar__CloseButton')]",
            # X 버튼 (텍스트)
            "//button[contains(text(), 'X') or contains(text(), '×')]",
            "//*[contains(text(), 'X') or contains(text(), '×')]",
            # 닫기 버튼 (텍스트)
            "//button[contains(text(), '닫기') or contains(text(), 'Close')]",
            "//*[contains(text(), '닫기') or contains(text(), 'Close')]",
            # aria-label
            "//button[contains(@aria-label, '닫기') or contains(@aria-label, 'close')]",
            "//*[@aria-label='닫기' or @aria-label='close' or @aria-label='Close']",
            # class 기반 (더 포괄적)
            "//*[contains(@class, 'close') or contains(@class, 'CloseButton')]",
            "//button[contains(@class, 'close') or contains(@class, 'CloseButton')]",
            "//div[contains(@class, 'close') or contains(@class, 'CloseButton')]",
            "//*[contains(@class, 'close') and (contains(@class, 'button') or contains(@class, 'btn'))]",
            # data 속성
            "//button[contains(@data-testid, 'close')]",
            "//*[@data-role='close']",
            # 일반적인 닫기 아이콘
            "//*[contains(@class, 'icon-close') or contains(@class, 'close-icon')]",
            # role 속성
            "//*[@role='button' and (contains(@class, 'close') or contains(@aria-label, 'close'))]",
        ]
        
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    try:
                        if elem.is_displayed() and elem.is_enabled():
                            # 스크롤해서 보이도록
                            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                            time.sleep(0.2)
                            
                            # 클릭 시도
                            try:
                                elem.click()
                                logger.info(f"이벤트 배너 닫기 성공: {selector}")
                                time.sleep(1)  # 닫힐 시간 대기
                                return True
                            except:
                                # JavaScript 클릭 시도
                                driver.execute_script("arguments[0].click();", elem)
                                logger.info(f"이벤트 배너 닫기 성공 (JS): {selector}")
                                time.sleep(1)
                                return True
                    except:
                        continue
            except:
                continue
        
        logger.warning("이벤트 배너 닫기 버튼을 찾지 못했습니다")
        return False
        
    except Exception as e:
        logger.error(f"이벤트 배너 닫기 중 오류: {e}")
        return False


def _is_main_page_deprecated(driver: webdriver.Chrome, original_url: str) -> bool:
    """
    현재 페이지가 메인 페이지인지 확인
    
    Args:
        driver: Selenium WebDriver
        original_url: 원래 접속하려던 URL
        
    Returns:
        메인 페이지인지 여부 (bool)
    """
    try:
        current_url = driver.current_url
        
        # URL 비교 (도메인만 비교)
        from urllib.parse import urlparse
        original_domain = urlparse(original_url).netloc
        current_domain = urlparse(current_url).netloc
        
        if original_domain != current_domain:
            logger.debug(f"도메인이 다름: {original_domain} != {current_domain}")
            return False
        
        # 메인 페이지 URL 패턴 확인
        main_page_patterns = [
            '/',  # 루트
            '/main',
            '/index',
            '/home',
        ]
        
        current_path = urlparse(current_url).path.rstrip('/')
        
        # 이벤트 페이지 패턴 제외
        event_patterns = [
            '/campaign',
            '/event',
            '/promotion',
            '/sale',
            '/popup',
            '/modal',
        ]
        
        if any(pattern in current_path for pattern in event_patterns):
            logger.debug(f"이벤트 페이지 패턴 감지: {current_path}")
            return False
        
        # 메인 페이지 패턴 확인
        if current_path == '' or current_path == '/' or any(pattern in current_path for pattern in main_page_patterns):
            logger.debug(f"메인 페이지로 판단: {current_url}")
            return True
        
        # 추가 확인: 네비게이션 메뉴가 있는지 확인
        nav_selectors = [
            "//nav",
            "//*[contains(@class, 'nav')]",
            "//*[contains(@class, 'menu')]",
            "//*[contains(@class, 'gnb')]",  # Global Navigation Bar
            "//*[contains(@id, 'nav')]",
            "//*[contains(@id, 'menu')]",
        ]
        
        for selector in nav_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.debug(f"네비게이션 메뉴 발견: {selector}")
                    return True
            except:
                continue
        
        logger.debug(f"메인 페이지가 아닌 것으로 판단: {current_url}")
        return False
        
    except Exception as e:
        logger.warning(f"메인 페이지 확인 중 오류: {e}")
        return False


def _handle_event_banner_deprecated(
    driver: webdriver.Chrome,
    original_url: str,
    max_attempts: int = 3
) -> tuple[bool, str]:
    """
    이벤트 배너가 있으면 닫고 메인 페이지로 이동
    
    Args:
        driver: Selenium WebDriver
        original_url: 원래 접속하려던 URL
        max_attempts: 최대 시도 횟수
        
    Returns:
        (성공 여부, 현재 URL) 튜플
    """
    try:
        # 현재 URL 확인
        current_url = driver.current_url
        logger.info(f"원래 URL: {original_url}")
        logger.info(f"현재 URL: {current_url}")
        
        # 이미 메인 페이지인지 확인
        if is_main_page(driver, original_url):
            logger.info("이미 메인 페이지입니다")
            return True, current_url
        
        # 이벤트 배너 감지
        if not detect_event_banner(driver):
            logger.info("이벤트 배너가 감지되지 않았습니다")
            # 메인 페이지가 아니지만 이벤트 배너도 아닌 경우
            # 원래 URL로 이동 시도
            try:
                driver.get(original_url)
                time.sleep(2)
                if is_main_page(driver, original_url):
                    return True, driver.current_url
            except:
                pass
            return False, current_url
        
        # 이벤트 배너 닫기 시도
        logger.info("이벤트 배너 감지, 닫기 시도...")
        for attempt in range(max_attempts):
            logger.info(f"닫기 시도 {attempt + 1}/{max_attempts}")
            
            if close_event_banner(driver):
                time.sleep(2)  # 페이지 변화 대기
                
                # 메인 페이지인지 확인
                if is_main_page(driver, original_url):
                    logger.info("메인 페이지로 이동 성공")
                    return True, driver.current_url
                
                # 여전히 이벤트 페이지인 경우 원래 URL로 이동 시도
                if detect_event_banner(driver):
                    logger.info("여전히 이벤트 페이지입니다. 원래 URL로 이동 시도...")
                    try:
                        # 쿠키 설정으로 이벤트 페이지 건너뛰기 시도
                        try:
                            driver.add_cookie({'name': 'skip_event', 'value': 'true'})
                        except:
                            pass
                        
                        # 원래 URL로 이동
                        driver.get(original_url)
                        time.sleep(3)
                        
                        # 메인 페이지인지 확인
                        if is_main_page(driver, original_url):
                            return True, driver.current_url
                        
                        # 여전히 이벤트 페이지인 경우, 메인 페이지의 특정 경로로 직접 이동 시도
                        from urllib.parse import urlparse
                        parsed = urlparse(original_url)
                        main_paths = [
                            f"{parsed.scheme}://{parsed.netloc}/",
                            f"{parsed.scheme}://{parsed.netloc}/main",
                            f"{parsed.scheme}://{parsed.netloc}/index",
                        ]
                        
                        for main_path in main_paths:
                            try:
                                driver.get(main_path)
                                time.sleep(2)
                                if is_main_page(driver, original_url):
                                    return True, driver.current_url
                            except:
                                continue
                                
                    except Exception as e:
                        logger.warning(f"원래 URL로 이동 실패: {e}")
            
            time.sleep(1)
        
        logger.warning("이벤트 배너를 닫고 메인 페이지로 이동하지 못했습니다")
        return False, driver.current_url
        
    except Exception as e:
        logger.error(f"이벤트 배너 처리 중 오류: {e}")
        return False, driver.current_url

