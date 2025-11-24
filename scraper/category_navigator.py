"""
카테고리 네비게이션 모듈
메인 페이지에서 카테고리를 탐지하고 각 카테고리 페이지로 이동하여 상품을 크롤링합니다.
"""
from typing import List, Optional, Set
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse

from scraper.product_parser import parse_products, Product
from auto_posting.browser_utils import setup_browser
from utils.logger import logger


def detect_category_links(driver: webdriver.Chrome, base_url: str) -> List[dict]:
    """
    메인 페이지에서 카테고리 링크 자동 탐지 (범용)
    다양한 사이트 구조에 대응하는 다층적 탐지 전략 사용
    
    Args:
        driver: Selenium WebDriver
        base_url: 기본 URL
        
    Returns:
        카테고리 정보 리스트 [{'name': '카테고리명', 'url': 'URL', 'element': element, 'score': float}]
    """
    logger.info("카테고리 링크 탐지 시작 (범용 모드)")
    
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    base_path = parsed_base.path.rstrip('/')
    
    candidates = []
    seen_urls: Set[str] = set()
    
    # 성능 최적화: implicit wait 임시 비활성화
    original_implicit_wait = driver.timeouts.implicit_wait
    driver.implicitly_wait(1)  # 1초로 단축
    
    # 제외할 텍스트 (버튼/시스템 텍스트)
    exclude_texts = {
        '로그인', '회원가입', '로그아웃', '마이페이지', '장바구니', '주문조회',
        '검색', '검색하기', '더보기', '전체보기', '홈', 'home', 'main',
        'login', 'signup', 'sign in', 'register', 'cart', 'basket',
        'search', 'more', 'all', '전체', '메인', '홈으로'
    }
    
    # 제외할 URL 패턴
    exclude_url_patterns = [
        r'javascript:', r'#', r'mailto:', r'tel:',
        r'/login', r'/signup', r'/register', r'/cart', r'/basket',
        r'/search', r'/mypage', r'/account'
    ]
    
    def is_valid_category_link(href: str, text: str) -> tuple[bool, float]:
        """
        링크가 유효한 카테고리 링크인지 검증하고 점수 반환
        
        Returns:
            (유효 여부, 점수)
        """
        if not href:
            return False, 0.0
        
        # 제외 패턴 확인
        for pattern in exclude_url_patterns:
            if re.search(pattern, href, re.I):
                return False, 0.0
        
        # 절대 URL로 변환
        if not href.startswith(('http://', 'https://')):
            href = urljoin(base_url, href)
        
        parsed_href = urlparse(href)
        
        # 외부 링크 제외
        if parsed_href.netloc != base_domain:
            return False, 0.0
        
        # 메인 페이지와 동일한 경우 제외
        if href == base_url or href == base_url + '/' or href.rstrip('/') == base_url:
            return False, 0.0
        
        # 텍스트 검증
        text_lower = text.lower().strip()
        if text_lower in exclude_texts or len(text) < 1 or len(text) > 50:
            return False, 0.0
        
        # 점수 계산
        score = 0.0
        
        # URL 패턴 점수
        href_lower = href.lower()
        category_keywords = ['category', 'cate', 'cat', 'catalog', 'shop', 'goods', 'product', 'item', 'list']
        for keyword in category_keywords:
            if keyword in href_lower:
                score += 0.3
                break
        
        # 상대 경로 점수 (/, /category/, /shop/ 등)
        if parsed_href.path and parsed_href.path != '/':
            path_parts = parsed_href.path.strip('/').split('/')
            if len(path_parts) >= 1:
                score += 0.2
        
        # 쿼리 파라미터 점수
        if parsed_href.query:
            query_lower = parsed_href.query.lower()
            if any(kw in query_lower for kw in ['category', 'cat', 'cate', 'type', 'kind']):
                score += 0.2
        
        # 텍스트 길이 점수 (2-20자가 이상적)
        if 2 <= len(text) <= 20:
            score += 0.1
        
        # 기본 점수
        score += 0.2
        
        return True, min(score, 1.0)
    
    # 전략 1: 네비게이션 영역에서 찾기
    nav_selectors = [
        'nav a',
        '.nav a', '.navigation a', '.menu a', '.menubar a',
        'header nav a', 'header .nav a', 'header .menu a',
        '.gnb a', '.gnb-nav a', '.main-menu a', '.main-nav a',
        '#nav a', '#navigation a', '#menu a'
    ]
    
    for selector in nav_selectors:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
            for link in links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    if not text:
                        text = link.get_attribute('aria-label') or link.get_attribute('title') or ''
                    
                    is_valid, score = is_valid_category_link(href, text)
                    if is_valid and href not in seen_urls:
                        seen_urls.add(href)
                        candidates.append({
                            'name': text,
                            'url': href,
                            'element': link,
                            'score': score + 0.3  # 네비게이션 영역 보너스
                        })
                except Exception:
                    continue
        except Exception:
            continue
    
    # 전략 2: 반복되는 링크 구조 찾기 (ul > li > a 패턴)
    list_selectors = [
        'ul li a', 'ol li a',
        '.menu-list li a', '.nav-list li a',
        '.category-list li a', '.item-list li a'
    ]
    
    for selector in list_selectors:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(links) >= 3:  # 3개 이상 반복되면 메뉴일 가능성
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        text = link.text.strip()
                        if not text:
                            text = link.get_attribute('aria-label') or link.get_attribute('title') or ''
                        
                        is_valid, score = is_valid_category_link(href, text)
                        if is_valid and href not in seen_urls:
                            seen_urls.add(href)
                            candidates.append({
                                'name': text,
                                'url': href,
                                'element': link,
                                'score': score + 0.2  # 리스트 구조 보너스
                            })
                    except Exception:
                        continue
        except Exception:
            continue
    
    # 전략 3: 같은 클래스를 가진 여러 링크 찾기
    try:
        # 클래스명에 menu, nav, category가 포함된 요소 찾기
        menu_containers = driver.find_elements(
            By.CSS_SELECTOR,
            '[class*="menu" i], [class*="nav" i], [class*="category" i], [class*="cate" i]'
        )
        
        for container in menu_containers:
            try:
                links = container.find_elements(By.TAG_NAME, 'a')
                if len(links) >= 3:  # 3개 이상 링크가 있으면 메뉴일 가능성
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            text = link.text.strip()
                            if not text:
                                text = link.get_attribute('aria-label') or link.get_attribute('title') or ''
                            
                            is_valid, score = is_valid_category_link(href, text)
                            if is_valid and href not in seen_urls:
                                seen_urls.add(href)
                                candidates.append({
                                    'name': text,
                                    'url': href,
                                    'element': link,
                                    'score': score + 0.1
                                })
                        except Exception:
                            continue
            except Exception:
                continue
    except Exception:
        pass
    
    # 전략 4: 명시적인 카테고리 키워드가 있는 링크
    category_keywords = ['category', 'cate', 'cat', 'catalog', 'shop', 'goods', 'product']
    for keyword in category_keywords:
        try:
            links = driver.find_elements(
                By.CSS_SELECTOR,
                f'a[href*="{keyword}" i]'
            )
            for link in links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    if not text:
                        text = link.get_attribute('aria-label') or link.get_attribute('title') or ''
                    
                    is_valid, score = is_valid_category_link(href, text)
                    if is_valid and href not in seen_urls:
                        seen_urls.add(href)
                        candidates.append({
                            'name': text,
                            'url': href,
                            'element': link,
                            'score': score + 0.4  # 명시적 키워드 보너스
                        })
                except Exception:
                    continue
        except Exception:
            continue
    
    # 중복 제거 및 점수 기반 정렬
    unique_candidates = {}
    for candidate in candidates:
        url = candidate['url']
        if url not in unique_candidates or candidate['score'] > unique_candidates[url]['score']:
            unique_candidates[url] = candidate
    
    # 점수 순으로 정렬
    sorted_categories = sorted(
        unique_candidates.values(),
        key=lambda x: x['score'],
        reverse=True
    )
    
    logger.info(f"총 {len(sorted_categories)}개 카테고리 후보 발견")
    
    # 상위 점수 카테고리만 반환 (점수 0.3 이상)
    filtered_categories = [cat for cat in sorted_categories if cat['score'] >= 0.3]
    
    logger.info(f"필터링 후 {len(filtered_categories)}개 카테고리 선택")
    
    # implicit wait 복원
    driver.implicitly_wait(original_implicit_wait)
    
    return filtered_categories


def navigate_to_category(
    driver: webdriver.Chrome, 
    category: dict, 
    use_hover: bool = False,
    wait_time: int = 2
) -> bool:
    """
    카테고리 페이지로 이동 (hover/click 처리)
    
    Args:
        driver: Selenium WebDriver
        category: 카테고리 정보 {'name': str, 'url': str, 'element': WebElement}
        use_hover: hover가 필요한 경우 True
        wait_time: 대기 시간 (초)
        
    Returns:
        이동 성공 여부
    """
    try:
        element = category.get('element')
        url = category['url']
        name = category['name']
        
        logger.info(f"카테고리 이동: {name} -> {url}")
        
        # 방법 1: 직접 URL로 이동 (가장 안정적)
        if not use_hover or not element:
            driver.get(url)
            time.sleep(wait_time)
            return True
        
        # 방법 2: hover 후 click
        if use_hover and element:
            try:
                # 요소가 보이는지 확인
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # hover
                ActionChains(driver).move_to_element(element).perform()
                time.sleep(0.3)  # 0.5초 -> 0.3초
                
                # click
                element.click()
                time.sleep(min(wait_time, 1))  # 최대 1초로 제한
                
                # URL 변경 확인
                current_url = driver.current_url
                if url in current_url or current_url in url:
                    return True
            except Exception as e:
                logger.warning(f"hover/click 실패, 직접 URL 이동: {e}")
                driver.get(url)
                time.sleep(wait_time)
                return True
        
        return True
        
    except Exception as e:
        logger.error(f"카테고리 이동 실패: {category.get('name', 'Unknown')} - {e}")
        return False


def crawl_category_products(
    driver: webdriver.Chrome,
    category_url: str,
    base_url: str
) -> List[Product]:
    """
    카테고리 페이지에서 상품 크롤링
    
    Args:
        driver: Selenium WebDriver
        category_url: 카테고리 페이지 URL
        base_url: 기본 URL
        
    Returns:
        상품 정보 리스트
    """
    try:
        # 페이지 로드 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # 상품 리스트 로딩 대기 (최소화)
        try:
            WebDriverWait(driver, 3).until(  # 5초 -> 3초
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass
        
        time.sleep(0.5)  # 추가 로딩 대기 (1초 -> 0.5초)
        
        # HTML 추출
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # 상품 파싱
        products = parse_products(soup, category_url)
        
        logger.info(f"카테고리에서 {len(products)}개 상품 추출: {category_url}")
        return products
        
    except Exception as e:
        logger.error(f"카테고리 상품 크롤링 실패: {category_url} - {e}")
        return []


def crawl_all_categories(
    url: str,
    max_categories: Optional[int] = None,
    use_hover: bool = False,
    headless: bool = True
) -> List[Product]:
    """
    메인 페이지에서 모든 카테고리를 탐지하고 각 카테고리의 상품을 크롤링
    
    Args:
        url: 메인 페이지 URL
        max_categories: 최대 처리할 카테고리 수 (None이면 모두 처리)
        use_hover: hover가 필요한 경우 True
        headless: 헤드리스 모드
        
    Returns:
        모든 카테고리의 상품 정보 통합 리스트
    """
    logger.info(f"카테고리 전체 크롤링 시작: {url}")
    
    driver: Optional[webdriver.Chrome] = None
    all_products: List[Product] = []
    
    try:
        # 브라우저 설정
        driver = setup_browser(headless=headless)
        driver.implicitly_wait(3)  # 10초 -> 3초로 단축
        
        # 메인 페이지 접속
        driver.get(url)
        logger.info("메인 페이지 로드 완료")
        
        # 페이지 로드 대기 (타임아웃 단축)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except TimeoutException:
            pass  # 타임아웃되어도 계속 진행
        time.sleep(1)  # 추가 로딩 대기 (2초 -> 1초)
        
        # 카테고리 링크 탐지
        categories = detect_category_links(driver, url)
        
        if not categories:
            logger.warning("카테고리를 찾을 수 없습니다. 메인 페이지에서 직접 크롤링 시도")
            # 메인 페이지에서 직접 크롤링
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            products = parse_products(soup, url)
            return products
        
        # 카테고리 수 제한
        if max_categories:
            categories = categories[:max_categories]
        
        logger.info(f"{len(categories)}개 카테고리 처리 시작")
        
        # 각 카테고리 순회
        for i, category in enumerate(categories, 1):
            logger.info(f"[{i}/{len(categories)}] 카테고리 처리: {category['name']}")
            
            # 카테고리 페이지로 이동
            if not navigate_to_category(driver, category, use_hover=use_hover):
                logger.warning(f"카테고리 이동 실패, 건너뜀: {category['name']}")
                continue
            
            # 상품 크롤링
            products = crawl_category_products(driver, category['url'], url)
            all_products.extend(products)
            
            logger.info(f"카테고리 '{category['name']}' 완료: {len(products)}개 상품")
            
            # 메인 페이지로 돌아가기 (다음 카테고리를 위해) - 최적화: 마지막 카테고리는 생략
            if i < len(categories):
                driver.get(url)
                time.sleep(1)  # 2초 -> 1초
        
        logger.info(f"전체 크롤링 완료: 총 {len(all_products)}개 상품")
        return all_products
        
    except Exception as e:
        logger.error(f"카테고리 크롤링 중 오류: {e}")
        return all_products
        
    finally:
        if driver:
            driver.quit()
            logger.debug("브라우저 종료")

