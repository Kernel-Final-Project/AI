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

from scraper.ssr_csr_checker import check_ssr_csr, CheckResult
from auto_posting.browser_utils import setup_browser
from utils.logger import logger


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

