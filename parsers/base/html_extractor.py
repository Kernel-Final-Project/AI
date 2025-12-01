"""
HTML 추출 모듈
SSR/CSR을 자동 판별하여 적절한 방법으로 HTML을 추출합니다.
"""
from typing import Optional, List, Tuple
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

from parsers.base.ssr_csr_checker import check_ssr_csr, CheckResult
from auto_posting.browser_utils import setup_browser
from utils.logger import logger
from urllib.parse import urlparse


def extract_html(
    url: str,
    method: Optional[str] = None,
    wait_time: int = 3,
    timeout: int = 10,
    implicit_wait_time: int = 10,
    explicit_wait_timeout: int = 10
) -> str:
    """
    URL에서 HTML을 추출합니다.
    method가 지정되지 않으면 자동으로 SSR/CSR을 판별하여 적절한 방법을 선택합니다.
    
    Args:
        url: 추출할 URL
        method: 추출 방법 ("requests", "selenium", None=자동)
        wait_time: Selenium 사용 시 대기 시간 (초) - deprecated, explicit wait 사용
        timeout: 요청 타임아웃 (초)
        implicit_wait_time: Selenium Implicit wait 시간 (초, 기본값: 10)
        explicit_wait_timeout: Selenium Explicit wait 타임아웃 (초, 기본값: 10)
        
    Returns:
        추출된 HTML 문자열
    """
    logger.info(f"HTML 추출 시작: {url} (method: {method or '자동'})")
    
    # 방법이 지정되지 않으면 자동 판별
    if method is None:
        check_result = check_ssr_csr(url, timeout=timeout)
        method = _select_method(check_result)
        logger.info(f"자동 판별 결과: {check_result.rendering_type} → {method} 사용")
    
    # 방법에 따라 HTML 추출
    if method == "requests":
        html, soup = _extract_with_requests(url, timeout)
        return html  # 기존 호환성을 위해 HTML 문자열만 반환
    elif method == "selenium":
        return _extract_with_selenium(
            url,
            wait_time=wait_time,
            implicit_wait_time=implicit_wait_time,
            explicit_wait_timeout=explicit_wait_timeout
        )
    else:
        raise ValueError(f"지원하지 않는 방법: {method}")


def _select_method(check_result: CheckResult) -> str:
    """
    판별 결과에 따라 적절한 추출 방법을 선택합니다.
    
    Args:
        check_result: SSR/CSR 판별 결과
        
    Returns:
        추출 방법 ("requests" 또는 "selenium")
    """
    if check_result.rendering_type == "SSR":
        return "requests"
    elif check_result.rendering_type == "CSR":
        return "selenium"
    elif check_result.rendering_type == "HYBRID":
        # 하이브리드의 경우 콘텐츠가 있으면 requests, 없으면 selenium
        if check_result.has_content:
            return "requests"
        else:
            return "selenium"
    else:
        # UNKNOWN의 경우 일단 requests 시도, 실패하면 selenium
        return "requests"


def _extract_with_requests(url: str, timeout: int = 10) -> Tuple[str, BeautifulSoup]:
    """
    requests를 사용하여 HTML을 추출하고 BeautifulSoup로 파싱합니다.
    
    Args:
        url: 추출할 URL
        timeout: 요청 타임아웃 (초)
        
    Returns:
        (HTML 문자열, BeautifulSoup 객체) 튜플
    """
    logger.debug(f"requests로 HTML 추출: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 1. HTTP 요청
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # status code 검증
        response.encoding = response.apparent_encoding  # 인코딩 자동 감지
        
        html = response.text
        logger.debug(f"HTML 추출 완료: {len(html)} bytes")
        
        # 2. BeautifulSoup로 DOM 파싱
        soup = BeautifulSoup(html, 'html.parser')
        logger.debug("BeautifulSoup로 DOM 파싱 완료")
        
        # 3. HTML 구조 검증
        _validate_html_structure(soup, html)
        
        return html, soup
        
    except requests.exceptions.RequestException as e:
        logger.error(f"requests로 HTML 추출 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"HTML 파싱 또는 검증 실패: {e}")
        raise


def _validate_html_structure(soup: BeautifulSoup, html: str) -> None:
    """
    HTML 구조가 비어있지 않은지 검증합니다.
    
    Args:
        soup: BeautifulSoup 객체
        html: HTML 문자열
        
    Raises:
        ValueError: HTML 구조가 비어있거나 유효하지 않은 경우
    """
    # 1. HTML 길이 검증
    if len(html.strip()) == 0:
        raise ValueError("HTML이 비어있습니다")
    
    # 2. body 태그 존재 확인
    body = soup.find('body')
    if not body:
        logger.warning("body 태그를 찾을 수 없습니다")
        # body가 없어도 계속 진행 (일부 사이트는 body 없이도 동작)
    
    # 3. 텍스트 내용 확인
    if body:
        body_text = body.get_text(strip=True)
        if len(body_text) < 10:  # 최소 10자 이상의 텍스트가 있어야 함
            logger.warning(f"body 내 텍스트가 너무 적습니다: {len(body_text)}자")
    else:
        # body가 없으면 전체 텍스트 확인
        all_text = soup.get_text(strip=True)
        if len(all_text) < 10:
            logger.warning(f"전체 텍스트가 너무 적습니다: {len(all_text)}자")
    
    logger.debug("HTML 구조 검증 완료")


def _wait_for_dom_elements(
    driver: webdriver.Chrome,
    selectors: Optional[List[str]] = None,
    timeout: int = 10
) -> bool:
    """
    주요 DOM 요소들이 로드될 때까지 대기합니다.
    
    Args:
        driver: WebDriver 인스턴스
        selectors: 확인할 CSS 선택자 리스트 (None이면 기본 선택자 사용)
        timeout: 각 요소 대기 시간 (초)
        
    Returns:
        하나 이상의 요소가 로드되었으면 True
    """
    if selectors is None:
        # 기본 주요 DOM 요소 선택자들
        selectors = [
            'body',  # 기본 body
            'article',  # 아티클
            'main',  # 메인 콘텐츠
            '.content', '#content',  # 콘텐츠 영역
            '.product', '.item', '.product-item',  # 상품 관련
            '[class*="product"]', '[class*="item"]',  # 상품 관련 (부분 일치)
            'h1', 'h2', 'h3',  # 제목
            'p',  # 문단
        ]
    
    wait = WebDriverWait(driver, timeout)
    loaded_count = 0
    
    for selector in selectors:
        try:
            # CSS 선택자로 요소 찾기
            if selector.startswith('#'):
                # ID 선택자
                element_id = selector[1:]
                wait.until(EC.presence_of_element_located((By.ID, element_id)))
                loaded_count += 1
                logger.debug(f"DOM 요소 로드 확인: {selector}")
            elif selector.startswith('.'):
                # Class 선택자
                class_name = selector[1:]
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
                loaded_count += 1
                logger.debug(f"DOM 요소 로드 확인: {selector}")
            elif selector.startswith('[') and 'class*=' in selector:
                # 속성 선택자 (class*="...")
                import re
                match = re.search(r'class\*="([^"]+)"', selector)
                if match:
                    class_part = match.group(1)
                    # XPath로 부분 일치 검색
                    xpath = f"//*[contains(@class, '{class_part}')]"
                    wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    loaded_count += 1
                    logger.debug(f"DOM 요소 로드 확인: {selector}")
            else:
                # 태그 선택자
                wait.until(EC.presence_of_element_located((By.TAG_NAME, selector)))
                loaded_count += 1
                logger.debug(f"DOM 요소 로드 확인: {selector}")
        except Exception:
            # 해당 요소가 없어도 계속 진행 (다른 요소 확인)
            logger.debug(f"DOM 요소 로드 실패 (무시): {selector}")
            continue
    
    if loaded_count > 0:
        logger.info(f"주요 DOM 요소 {loaded_count}개 로드 확인 완료")
        return True
    else:
        logger.warning("주요 DOM 요소 로드 확인 실패, 기본 body만 확인됨")
        return False


def _extract_with_selenium(
    url: str,
    wait_time: int = 3,
    custom_selectors: Optional[List[str]] = None,
    implicit_wait_time: int = 10,
    explicit_wait_timeout: int = 10
) -> str:
    """
    Selenium을 사용하여 HTML을 추출합니다.
    Implicit wait와 Explicit wait를 모두 적용합니다.
    
    Args:
        url: 추출할 URL
        wait_time: 페이지 로딩 대기 시간 (초) - deprecated, explicit wait 사용
        custom_selectors: 확인할 커스텀 CSS 선택자 리스트 (선택사항)
        implicit_wait_time: Implicit wait 시간 (초, 기본값: 10)
        explicit_wait_timeout: Explicit wait 타임아웃 (초, 기본값: 10)
        
    Returns:
        HTML 문자열
    """
    logger.debug(f"Selenium으로 HTML 추출: {url}")
    
    driver: Optional[webdriver.Chrome] = None
    
    try:
        # 브라우저 설정 (헤드리스 모드로 설정 가능)
        driver = setup_browser(headless=True)
        
        # Implicit wait 설정 (이미 setup_browser에서 설정되지만 명시적으로 재설정)
        driver.implicitly_wait(implicit_wait_time)
        logger.debug(f"Implicit wait 설정: {implicit_wait_time}초")
        
        # 페이지 로드
        driver.get(url)
        logger.debug(f"페이지 로드 완료: {url}")
        
        # Explicit wait로 페이지 로드 완료 대기
        # 1. document.readyState가 'complete'가 될 때까지 대기
        try:
            WebDriverWait(driver, explicit_wait_timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            logger.debug("페이지 로드 상태 확인 완료 (document.readyState = complete)")
        except Exception:
            logger.warning("페이지 로드 상태 확인 타임아웃, 계속 진행")
        
        # 2. 기본 body 요소 확인 (Explicit wait)
        try:
            WebDriverWait(driver, explicit_wait_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.debug("body 요소 로드 확인 완료 (Explicit wait)")
        except Exception:
            logger.warning("body 요소 대기 중 타임아웃, 계속 진행")
        
        # 3. 주요 DOM 요소들 확인 (Explicit wait)
        _wait_for_dom_elements(driver, selectors=custom_selectors, timeout=explicit_wait_timeout)
        
        # 4. 이벤트 배너 처리 (메인 페이지로 이동)
        try:
            handle_event_banner_and_navigate_to_main(driver, url)
        except Exception as e:
            logger.warning(f"이벤트 배너 처리 중 오류 (무시하고 계속 진행): {e}")
        
        # HTML 추출
        html = driver.page_source
        
        logger.debug(f"HTML 추출 완료: {len(html)} bytes")
        return html
        
    except Exception as e:
        logger.error(f"Selenium으로 HTML 추출 실패: {e}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.debug("브라우저 종료")


def load_html_ssr(url: str, timeout: int = 10) -> Tuple[str, BeautifulSoup]:
    """
    SSR 사이트에서 HTML을 로드하고 BeautifulSoup로 파싱합니다.
    
    Args:
        url: 로드할 URL
        timeout: 요청 타임아웃 (초)
        
    Returns:
        (HTML 문자열, BeautifulSoup 객체) 튜플
    """
    return _extract_with_requests(url, timeout)


def load_html_csr(
    url: str,
    custom_selectors: Optional[List[str]] = None,
    implicit_wait_time: int = 10,
    explicit_wait_timeout: int = 10
) -> Tuple[str, BeautifulSoup]:
    """
    CSR 사이트에서 HTML을 로드하고 BeautifulSoup로 파싱합니다.
    
    Args:
        url: 로드할 URL
        custom_selectors: 확인할 커스텀 CSS 선택자 리스트 (선택사항)
        implicit_wait_time: Implicit wait 시간 (초, 기본값: 10)
        explicit_wait_timeout: Explicit wait 타임아웃 (초, 기본값: 10)
        
    Returns:
        (HTML 문자열, BeautifulSoup 객체) 튜플
    """
    logger.info(f"CSR 사이트 HTML 로드 시작: {url}")
    
    # Selenium으로 HTML 추출
    html = _extract_with_selenium(
        url,
        custom_selectors=custom_selectors,
        implicit_wait_time=implicit_wait_time,
        explicit_wait_timeout=explicit_wait_timeout
    )
    
    # BeautifulSoup로 파싱
    soup = BeautifulSoup(html, 'html.parser')
    logger.debug("BeautifulSoup로 DOM 파싱 완료")
    
    # HTML 구조 검증
    _validate_html_structure(soup, html)
    
    return html, soup


def extract_html_with_fallback(
    url: str,
    wait_time: int = 3,
    timeout: int = 10,
    implicit_wait_time: int = 10,
    explicit_wait_timeout: int = 10
) -> str:
    """
    HTML을 추출합니다. requests 실패 시 자동으로 selenium으로 재시도합니다.
    
    Args:
        url: 추출할 URL
        wait_time: Selenium 사용 시 대기 시간 (초) - deprecated, explicit wait 사용
        timeout: 요청 타임아웃 (초)
        implicit_wait_time: Selenium Implicit wait 시간 (초, 기본값: 10)
        explicit_wait_timeout: Selenium Explicit wait 타임아웃 (초, 기본값: 10)
        
    Returns:
        추출된 HTML 문자열
    """
    logger.info(f"HTML 추출 시작 (fallback 모드): {url}")
    
    # 먼저 requests 시도
    try:
        html, soup = _extract_with_requests(url, timeout)
        return html  # 기존 호환성을 위해 HTML 문자열만 반환
    except Exception as e:
        logger.warning(f"requests 실패, selenium으로 재시도: {e}")
        return _extract_with_selenium(
            url,
            wait_time=wait_time,
            implicit_wait_time=implicit_wait_time,
            explicit_wait_timeout=explicit_wait_timeout
        )


# ========== 이벤트 배너 처리 함수들 ==========

def detect_event_banner(driver: webdriver.Chrome) -> bool:
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
        
        # 실제 팝업/모달만 감지 (범용적인 방법)
        # 팝업/모달의 특징: 큰 크기, 높은 z-index, 배경 오버레이 등
        popup_modal_selectors = [
            "//*[contains(@class, 'modal')]",
            "//*[contains(@class, 'popup')]",
            "//*[contains(@class, 'overlay')]",
            "//*[contains(@class, 'dialog')]",
            "//*[@role='dialog']",
            "//*[@role='alertdialog']",
        ]
        
        for selector in popup_modal_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if not elem.is_displayed():
                        continue
                    
                    # 팝업/모달 특징 확인 (범용적)
                    try:
                        size = elem.size
                        # 큰 크기 (300x300 이상) = 팝업/모달 가능성
                        if size['width'] > 300 or size['height'] > 300:
                            z_index = driver.execute_script(
                                "return window.getComputedStyle(arguments[0]).zIndex", elem
                            )
                            # 높은 z-index (100 이상) = 팝업/모달 가능성
                            if z_index and z_index != 'auto' and int(z_index) > 100:
                                logger.debug(f"팝업/모달 감지: {selector}")
                                return True
                    except:
                        continue
            except:
                continue
        
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


def close_event_banner(driver: webdriver.Chrome, timeout: float = 5.0) -> bool:
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
            # AI 챗봇 특화 (우선 시도)
            "//*[contains(@class, 'ai') or contains(@class, 'AI')]//button[contains(@class, 'close')]",
            "//*[contains(@class, 'chatbot') or contains(@class, 'Chatbot')]//button[contains(@class, 'close')]",
            "//*[contains(@class, 'assistant') or contains(@class, 'Assistant')]//button[contains(@class, 'close')]",
            "//*[contains(@id, 'ai') or contains(@id, 'AI')]//button[contains(@class, 'close')]",
            "//*[contains(@id, 'chatbot') or contains(@id, 'Chatbot')]//button[contains(@class, 'close')]",
            "//*[contains(@class, 'ai') or contains(@class, 'AI')]//*[contains(@class, 'close')]",
            "//*[contains(@class, 'chatbot') or contains(@class, 'Chatbot')]//*[contains(@class, 'close')]",
            "//*[contains(@class, 'ai') or contains(@class, 'AI')]//*[contains(text(), 'X') or contains(text(), '×')]",
            "//*[contains(@class, 'chatbot') or contains(@class, 'Chatbot')]//*[contains(text(), 'X') or contains(text(), '×')]",
            # 무신사 특화
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


def is_main_page(driver: webdriver.Chrome, original_url: str) -> bool:
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


def handle_event_banner_and_navigate_to_main(
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
