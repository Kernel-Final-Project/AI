"""
카테고리 트리 추출기
BeautifulSoup 기반 - HTML 구조에서 카테고리 상하위 구조를 자동으로 찾는 기능
Selenium 통합 - 동적으로 열리는 submenu까지 추출
"""
from typing import Dict, Optional
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from utils.category_patterns import (
    CATEGORY_TAGS, 
    CATEGORY_ID_KEYWORDS,
    SUBMENU_SELECTORS
)
from scraper.html_category_detector import (
    find_category_candidates,
    filter_clickable_elements,
    detect_hover_needed
)
from scraper.category_interaction import find_selenium_element
from scraper.category_clicker import click_category_with_fallback
from scraper.category_interaction_detector import detect_menu_behavior
from utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import re


def is_category_container(tag: Tag) -> bool:
    """카테고리가 담길 가능성이 높은 컨테이너인지 체크"""
    # 태그 기반 체크
    if tag.name in CATEGORY_TAGS:
        return True
    
    # ID 기반 체크만 유지 (랜덤 class명 대응을 위해 class 체크 제거)
    element_id = tag.get("id", "").lower()
    if any(k in element_id for k in CATEGORY_ID_KEYWORDS):
        return True
    
    return False


def extract_category_text(tag: Tag) -> Optional[str]:
    """카테고리 텍스트를 깔끔하게 추출"""
    # <a> 태그가 있으면 <a>의 텍스트 우선 사용
    link = tag.find("a")
    if link:
        text = link.get_text(strip=True)
    else:
        text = tag.get_text(strip=True)
    
    # 너무 짧은 텍스트(1~2자)는 대부분 아이콘 또는 의미없음
    if len(text) < 2:
        return None
    
    # 너무 긴 텍스트(설명문 등)도 제외
    if len(text) > 40:
        return None
    
    return text

def has_menu_text(tag):
    text = tag.get_text(strip=True)
    if not text:
        return False
    if len(text) < 2 or len(text) > 20:
        return False
    if text.isdigit():
        return False
    return True


def extract_category_tree(
    tag: Tag,
    driver: Optional[webdriver.Chrome] = None,
    depth: int = 0,
    max_depth: int = 3
) -> Dict[str, Dict]:
    """
    재귀적으로 상위 → 하위 카테고리를 추출하는 핵심 함수
    (원본 구조 유지 + Selenium 통합)
    
    Args:
        tag: 카테고리 컨테이너 Tag
        driver: Selenium WebDriver (동적 submenu 추출용, 선택사항)
        depth: 현재 깊이
        max_depth: 최대 깊이 제한
    """
    if depth >= max_depth:
        return {}
    
    tree = {}
    
    # 1) 현재 컨테이너 내부에서 "직계 하위 메뉴" 후보 찾기
    candidate_children = tag.find_all(
        ["li", "div"],
        recursive=False  # 직계 자식만 탐색 → 구조 안정성 높음
    )
    
    logger.info(f"직계 자식 요소: {len(candidate_children)}개 (depth: {depth})")
    
    processed_count = 0
    text_extracted_count = 0
    
    for child in candidate_children:
        # 텍스트 추출 먼저 시도 (클릭 가능 여부와 관계없이)
        raw_text = child.get_text(strip=True)
        logger.debug(f"[디버깅] child 태그={child.name}, 클래스={child.get('class', [])}, 원본 텍스트='{raw_text[:100]}', 길이={len(raw_text)}")
        
        text = extract_category_text(child)
        if not text:
            # 텍스트가 없으면 스킵 (클릭 가능 여부와 관계없이)
            logger.warning(f"텍스트 추출 실패: 원본 텍스트='{raw_text[:50]}', 길이={len(raw_text)}, 태그={child.name}, 클래스={child.get('class', [])}")
            continue
        
        # 텍스트가 있으면 일단 처리 (클릭 가능한 요소 필터링 완화)
        processed_count += 1
        logger.info(f"[성공] 텍스트 추출 성공: '{text}' (태그={child.name})")
        
        text_extracted_count += 1
        
        # 중복 제거 (개선사항)
        if text in tree:
            continue
        
        # 3) 해당 child 내부에 추가 하위 메뉴가 있는지 확인
        submenus = child.find(["ul", "div"], recursive=False)
        
        if submenus and is_category_container(submenus):
            # 재귀적으로 하위 구조 추출
            tree[text] = extract_category_tree(submenus, driver, depth + 1, max_depth)
        else:
            # 하위 구조가 없음 → leaf node
            # 하지만 Selenium으로 동적 submenu 확인 (개선사항)
            # 속도 최적화: 상위 5개만 동적 분석 수행
            if driver and text_extracted_count <= 5:
                try:
                    selenium_elem = find_selenium_element(driver, child)
                    if selenium_elem:
                        # hover/click 기반 판별 (강화된 detect_menu_behavior 사용)
                        menu_behavior = detect_menu_behavior(
                            driver=driver,
                            bs4_tag=child,
                            selenium_element=selenium_elem,
                            use_dynamic=True
                        )
                        
                        logger.debug(f"카테고리 '{text}' 동작 방식: {menu_behavior}")
                        
                        opened_submenu_elem = None
                        
                        # 판별된 방식에 따라 처리
                        if menu_behavior == "hover":
                            # hover만 시도
                            from scraper.category_interaction import hover_element, hover_and_wait_for_submenu
                            hover_success = hover_element(driver, selenium_elem, wait_seconds=0.3)
                            if hover_success:
                                submenu_opened = hover_and_wait_for_submenu(driver, selenium_elem, timeout=2.0)
                                if submenu_opened:
                                    opened_submenu_elem = _find_opened_submenu(selenium_elem, driver)
                        elif menu_behavior == "click":
                            # click만 시도
                            try:
                                selenium_elem.click()
                                time.sleep(0.5)
                                opened_submenu_elem = _find_opened_submenu(selenium_elem, driver)
                            except Exception as e:
                                logger.debug(f"click 실패: {e}")
                        else:
                            # unknown이면 기존 fallback 방식 사용
                            success, method = click_category_with_fallback(
                                driver, selenium_elem, timeout=2.0
                            )
                            if success:
                                time.sleep(0.5)  # submenu 렌더링 대기
                                opened_submenu_elem = _find_opened_submenu(selenium_elem, driver)
                        
                        # 찾은 submenu를 BeautifulSoup으로 변환
                        if opened_submenu_elem:
                            try:
                                # WebElement의 innerHTML 가져오기
                                submenu_html = opened_submenu_elem.get_attribute("outerHTML")
                                if submenu_html:
                                    soup = BeautifulSoup(submenu_html, "html.parser")
                                    opened_submenu_tag = soup.find(["ul", "div"])
                                    
                                    if opened_submenu_tag and is_category_container(opened_submenu_tag):
                                        # 동적으로 열린 submenu에서 하위 카테고리 추출
                                        dynamic_children = extract_category_tree(
                                            opened_submenu_tag, driver, depth + 1, max_depth
                                        )
                                        if dynamic_children:
                                            tree[text] = dynamic_children
                                            logger.info(f"동적 submenu 추출 성공: {text} ({len(dynamic_children)}개 하위)")
                                            continue
                            except Exception as e:
                                logger.debug(f"submenu HTML 변환 실패 ({text}): {e}")
                except Exception as e:
                    logger.debug(f"동적 submenu 추출 실패 ({text}): {e}")
            
            # 하위 구조가 없음 → leaf node
            tree[text] = {}
    
    logger.info(f"트리 추출 결과 (depth {depth}): 처리된 요소 {processed_count}개, 텍스트 추출 {text_extracted_count}개, 최종 카테고리 {len(tree)}개")
    if processed_count > 0 and text_extracted_count == 0:
        logger.warning(f"처리된 요소는 있지만 텍스트 추출 실패 (depth {depth})")
    if text_extracted_count > 0 and len(tree) == 0:
        logger.warning(f"텍스트는 추출되었지만 트리에 추가되지 않음 (depth {depth})")
    return tree


def build_full_category_tree(
    html: str,
    driver: Optional[webdriver.Chrome] = None,
    use_dynamic: bool = True
) -> Dict[str, Dict]:
    """
    HTML 전체에서 가장 유력한 카테고리 컨테이너를 골라 트리 생성
    (SSR 사이트용 - BeautifulSoup 기반)
    
    Args:
        html: HTML 문자열
        driver: Selenium WebDriver (동적 submenu 추출용, 선택사항)
        use_dynamic: 동적 submenu 추출 사용 여부
    """
    # 디버깅: HTML 전체 길이 확인
    logger.info(f"HTML 전체 길이: {len(html)} 문자")
    
    # <header> 또는 <nav> 위치 자동 찾기
    html_lower = html.lower()
    header_pos = html_lower.find('<header')
    nav_pos = html_lower.find('<nav')
    
    start_pos = -1
    if header_pos != -1:
        start_pos = header_pos
        logger.info(f"<header> 태그 발견: 위치 {start_pos}")
    elif nav_pos != -1:
        start_pos = nav_pos
        logger.info(f"<nav> 태그 발견: 위치 {start_pos}")
    
    # 찾은 위치부터 150,000자 slicing (없으면 처음부터 150,000자)
    if start_pos != -1:
        sliced_html = html[start_pos:start_pos+150000]
        logger.info(f"파싱할 HTML: 위치 {start_pos}부터 150,000자 ({len(sliced_html)} 문자)")
    else:
        sliced_html = html[:150000]
        logger.info(f"<header>/<nav> 태그를 찾지 못해 처음부터 150,000자 파싱 ({len(sliced_html)} 문자)")
    
    logger.info(f"파싱할 HTML 처음 200자: {sliced_html[:200]}")
    
    soup = BeautifulSoup(sliced_html, "html.parser")

    # 디버깅: 파싱된 HTML 안에 있는 모든 태그 확인
    all_tags = soup.find_all(True, limit=500)  # 모든 태그 (성능 최적화: 상위 500개만)
    logger.info(f"파싱된 HTML 안에 있는 모든 태그 개수: {len(all_tags)}개 (limit=500)")
    
    if all_tags:
        logger.info(f"처음 10개 태그: {[tag.name for tag in all_tags[:10]]}")
        logger.info(f"마지막 10개 태그: {[tag.name for tag in all_tags[-10:]]}")
    
    # 디버깅: div 태그들 확인
    all_divs = soup.find_all("div", limit=100)  # 성능 최적화: 상위 100개만
    logger.info(f"파싱된 HTML 안에 있는 div 태그 개수: {len(all_divs)}개 (limit=100)")
    
    if all_divs:
        last_div = all_divs[-1]
        last_div_classes = last_div.get("class", [])
        last_div_id = last_div.get("id", "")
        last_div_text = last_div.get_text(strip=True)[:50] if last_div.get_text(strip=True) else ""
        logger.info(f"마지막 div 정보:")
        logger.info(f"  - 클래스: {last_div_classes}")
        logger.info(f"  - ID: {last_div_id}")
        logger.info(f"  - 텍스트 (처음 50자): {last_div_text}")
    
    # 디버깅: nav, ul, li 태그도 확인
    all_navs = soup.find_all("nav", limit=50)  # 성능 최적화
    all_uls = soup.find_all("ul", limit=100)  # 성능 최적화
    all_lis = soup.find_all("li", limit=200)  # 성능 최적화
    logger.info(f"파싱된 HTML 안에 있는 태그 개수 - nav: {len(all_navs)}, ul: {len(all_uls)}, li: {len(all_lis)}, div: {len(all_divs)}")

    containers = []
    for tag in soup.find_all(["nav", "ul","li","div"], limit=100):  # 성능 최적화: 상위 100개만
        if is_category_container(tag):
            # 모바일 메뉴 제외
            classes = " ".join(tag.get("class", [])).lower()
            element_id = tag.get("id", "").lower()
            if "mobile" in classes or "mobile" in element_id:
                continue
            containers.append(tag)
    
    logger.info(f"카테고리 컨테이너 후보: {len(containers)}개")

    containers = [
    tag for tag in containers 
    if has_menu_text(tag)
    ]
    logger.info(f"텍스트 필터링 후: {len(containers)}개")

    # 성능 개선: 같은 soup 객체를 사용하여 매칭 보장
    # soup 객체에서 직접 찾기 (새로운 soup 객체 생성 방지)
    from utils.category_patterns import CATEGORY_TAGS, CATEGORY_ID_KEYWORDS
    
    category_candidates = []
    for tag in soup.find_all(True, limit=500):  # 성능 최적화: 상위 500개만
        tag_name = tag.name.lower()
        element_id = tag.get("id", "")
        
        tag_match = tag_name in CATEGORY_TAGS
        id_match = False
        if element_id:
            id_match = any(keyword in element_id.lower() for keyword in CATEGORY_ID_KEYWORDS)
        
        # class 체크 제거 (랜덤 class명 대응)
        if tag_match or id_match:
            category_candidates.append(tag)
    
    clickable_candidates = filter_clickable_elements(category_candidates)
    logger.info(f"클릭 가능한 후보 개수: {len(clickable_candidates)}개")
    
    # 같은 soup 객체에서 찾은 것이므로 id 기반 매칭 가능
    clickable_set = set(id(t) for t in clickable_candidates)
    
    # 디버깅: 매칭 시도 로그
    matched_count = 0
    matched_by_direct = 0
    matched_by_child = 0
    
    filtered_containers = []
    for tag in containers:
        # 직접 매칭 확인
        if id(tag) in clickable_set:
            filtered_containers.append(tag)
            matched_count += 1
            matched_by_direct += 1
            continue
        
        # 자식 요소 매칭 확인
        children = tag.find_all(recursive=False, limit=10)
        if any(id(child) in clickable_set for child in children):
            filtered_containers.append(tag)
            matched_count += 1
            matched_by_child += 1
            continue
    
    logger.info(f"클릭 가능성 필터링 결과:")
    logger.info(f"  - 직접 매칭: {matched_by_direct}개")
    logger.info(f"  - 자식 매칭: {matched_by_child}개")
    logger.info(f"  - 총 매칭: {matched_count}개")
    logger.info(f"  - 필터링 후: {len(filtered_containers)}개")
    
    containers = filtered_containers

    if not containers:
        logger.warning("카테고리 컨테이너를 찾지 못했습니다")
        return {}
    
    # 2) 가장 상단에 있는 컨테이너(전체 카테고리를 포함하는 것) 선택
    # 개선: 3단계 필터링 (HTML 순서 → 위치 기반 → 상위 50개만 상세 평가)
    
    # 0단계: HTML 순서 기반 빠른 필터링 (상위 50개만 선택)
    # HTML에서 먼저 나타나는 요소가 상단에 있을 가능성이 높음
    logger.info("0단계: HTML 순서 기반 빠른 필터링 중...")
    # containers는 이미 HTML 순서대로 정렬되어 있으므로 상위 50개만 선택
    top_50_containers = containers[:min(50, len(containers))]
    logger.info(f"상위 50개 컨테이너 선택 완료 (HTML 순서 기반)")
    
    # 1단계: 위치 기반 빠른 필터링 (선택된 50개의 위치 점수만 계산)
    logger.info("1단계: 위치 기반 빠른 필터링 중...")
    position_scores = []
    for container in top_50_containers:
        position_score = 0
        if driver:
            try:
                # BeautifulSoup Tag → Selenium WebElement 변환
                selenium_elem = find_selenium_element(driver, container)
                if selenium_elem:
                    # 요소의 Y 좌표 확인 (화면 상단에서의 거리)
                    location = selenium_elem.location
                    y_coord = location.get('y', 10000)  # 기본값: 매우 아래
                    
                    # 상단일수록 높은 점수 (최대 1000점, y=0일 때)
                    # y=0 → 1000점, y=500 → 500점, y=1000 이상 → 0점
                    position_score = max(0, 1000 - y_coord)
            except Exception as e:
                logger.debug(f"위치 점수 계산 실패: {e}")
                position_score = 0
        else:
            # driver가 없으면 텍스트 길이로 대체 (위치 점수 대신)
            position_score = len(container.get_text(strip=True))
        
        position_scores.append((position_score, container))
    
    # 위치 점수로 정렬하여 상위 50개 선택
    position_scores.sort(key=lambda x: x[0], reverse=True)
    top_n = min(50, len(position_scores))
    top_containers = [container for _, container in position_scores[:top_n]]
    logger.info(f"상위 {top_n}개 컨테이너 선택 완료 (위치 기반 필터링)")
    
    # 2단계: 선택된 컨테이너만 클릭 가능 요소 점수 계산
    logger.info("2단계: 선택된 컨테이너 상세 평가 중...")
    # 이미 찾은 clickable_candidates 재사용 (전체 HTML 다시 파싱 방지)
    clickable = clickable_candidates  # 위에서 이미 찾은 것 재사용
    logger.info(f"클릭 가능한 카테고리 요소: {len(clickable)}개 (재사용)")
    
    container_scores = []
    for container, position_score in zip(top_containers, [score for score, _ in position_scores[:top_n]]):
        # 클릭 가능한 요소 개수 계산
        clickable_score = 0
        for clickable_elem in clickable:
            try:
                if container in clickable_elem.parents or container == clickable_elem:
                    clickable_score += 1
            except:
                pass
        
        # 최종 점수: 클릭 가능 요소 개수 + 위치 점수 (위치 점수는 0~1000 범위)
        # 클릭 가능 요소 개수가 더 중요하므로 위치 점수는 보조적으로 사용
        final_score = clickable_score + (position_score / 10)  # 위치 점수를 10으로 나눠서 보조 점수로 사용
        
        container_scores.append((final_score, clickable_score, position_score, container))
    
    # 점수가 높은 순으로 정렬
    container_scores.sort(key=lambda x: x[0], reverse=True)
    
    if container_scores and container_scores[0][0] > 0:
        root = container_scores[0][3]  # container는 4번째 요소
        final_score, clickable_score, position_score = container_scores[0][0], container_scores[0][1], container_scores[0][2]
        logger.info(f"최적 컨테이너 선택 (최종 점수: {final_score:.1f}, 클릭 가능: {clickable_score}, 위치: {position_score:.0f}, 태그: {root.name})")
    else:
        # 점수가 모두 0이면 텍스트 길이로 선택 (원본 로직)
        containers.sort(key=lambda x: len(x.get_text(strip=True)), reverse=True)
        root = containers[0]
        logger.info(f"컨테이너 선택 (fallback, 태그: {root.name}, 텍스트 길이: {len(root.get_text(strip=True))})")
    
    # 3) 트리 생성
    logger.info("카테고리 트리 추출 시작...")
    if use_dynamic and driver:
        tree = extract_category_tree(root, driver, depth=0, max_depth=3)
    else:
        tree = extract_category_tree(root, None, depth=0, max_depth=3)
    
    logger.info(f"카테고리 트리 추출 완료: {len(tree)}개 상위 카테고리")
    return tree


def build_category_tree_csr(
    driver: webdriver.Chrome,
    use_dynamic: bool = True
) -> Dict[str, Dict]:
    """
    CSR 사이트용 카테고리 트리 추출 (Selenium 직접 사용)
    CSS/XPath로 직접 요소를 찾아서 처리
    방법 1: 카테고리 위치를 더 강하게 제한
    
    Args:
        driver: Selenium WebDriver (필수)
        use_dynamic: 동적 submenu 추출 사용 여부
    
    Returns:
        카테고리 트리 딕셔너리
    """
    logger.info("CSR 사이트 - Selenium으로 직접 카테고리 탐지")
    
    if not driver:
        logger.error("CSR 방식은 driver가 필수입니다")
        return {}
    
    # 방법 1: 카테고리 위치를 더 강하게 제한
    # 우선순위 기반 탐색
    
    # 1순위: <header> 내부의 카테고리
    try:
        headers = driver.find_elements(By.CSS_SELECTOR, "header")
        for header in headers:
            # header 내부에서 nav, ul, category-menu 찾기
            navs = header.find_elements(By.CSS_SELECTOR, "nav, ul, [class*='category'], [class*='gnb'], [id*='category'], [id*='gnb']")
            if navs:
                largest = max(navs, key=lambda x: len(x.text))
                logger.info(f"<header> 내부 카테고리 발견: 텍스트 길이 {len(largest.text)}")
                return _extract_tree_from_selenium_element(largest, driver, use_dynamic)
    except Exception as e:
        logger.debug(f"<header> 내부 탐색 실패: {e}")
    
    # 2순위: <nav> 내부의 카테고리
    try:
        navs = driver.find_elements(By.CSS_SELECTOR, "nav")
        if navs:
            largest_nav = max(navs, key=lambda x: len(x.text))
            logger.info(f"<nav> 태그 발견: {len(navs)}개, 선택된 nav 텍스트 길이: {len(largest_nav.text)}")
            return _extract_tree_from_selenium_element(largest_nav, driver, use_dynamic)
    except Exception as e:
        logger.debug(f"<nav> 태그 찾기 실패: {e}")
    
    # 3순위: 특정 클래스/ID를 가진 <div> (구체적인 것부터, 자식 요소 개수로 우선순위 결정)
    category_selectors = [
        'div.over.category-menu-scroll.link_cover',  # 싸다구 실제 구조 (최우선)
        'div.category-menu',
        '[class*="category-menu"]',
        '[class*="category"]',
        'div.gnb',
        'div#gnb',
        '[class*="gnb"]',
        '[id*="gnb"]',
        '[id*="category"]',
        'div.header',
        'div#header'
    ]
    
    best_div = None
    best_score = 0
    
    for selector in category_selectors:
        try:
            divs = driver.find_elements(By.CSS_SELECTOR, selector)
            if divs:
                # 모바일 메뉴 제외
                valid_divs = []
                for div in divs:
                    classes = div.get_attribute("class") or ""
                    element_id = div.get_attribute("id") or ""
                    if "mobile" in classes.lower() or "mobile" in element_id.lower():
                        continue
                    if len(div.text.strip()) > 20:  # 의미있는 텍스트가 있으면
                        valid_divs.append(div)
                
                for div in valid_divs:
                    try:
                        # 자식 요소 개수 확인 (li, a 태그)
                        children_count = len(div.find_elements(By.CSS_SELECTOR, "li, a"))
                        # 점수 계산: 자식 요소 개수가 많을수록 높은 점수
                        score = children_count
                        
                        # 구체적인 선택자는 보너스 점수
                        if selector == 'div.over.category-menu-scroll.link_cover':
                            score += 1000  # 싸다구 구조는 최우선
                        elif 'category-menu' in selector:
                            score += 500
                        
                        if score > best_score:
                            best_score = score
                            best_div = div
                            logger.debug(f"더 나은 카테고리 div 발견 (selector: {selector}): 점수 {score}, 자식 요소 {children_count}개")
                    except Exception as e:
                        logger.debug(f"자식 요소 개수 확인 실패: {e}")
        except Exception as e:
            logger.debug(f"카테고리 div 찾기 실패 (selector: {selector}): {e}")
    
    if best_div and best_score >= 5:  # 최소 5개 이상의 자식 요소가 있어야 카테고리로 인정
        # 디버깅: 선택된 div의 상세 정보
        try:
            classes = best_div.get_attribute("class") or ""
            element_id = best_div.get_attribute("id") or ""
            all_children = best_div.find_elements(By.CSS_SELECTOR, "*")
            li_children = best_div.find_elements(By.CSS_SELECTOR, "li")
            a_children = best_div.find_elements(By.CSS_SELECTOR, "a")
            logger.info(f"최적 카테고리 div 선택: 점수 {best_score}")
            logger.info(f"  - class: {classes}")
            logger.info(f"  - id: {element_id}")
            logger.info(f"  - 전체 자식 요소: {len(all_children)}개")
            logger.info(f"  - li 요소: {len(li_children)}개")
            logger.info(f"  - a 요소: {len(a_children)}개")
            logger.info(f"  - 텍스트 길이: {len(best_div.text)}")
        except:
            pass
        
        return _extract_tree_from_selenium_element(best_div, driver, use_dynamic)
    
    # 4순위: 가장 큰 <ul> 찾기 (fallback)
    try:
        uls = driver.find_elements(By.CSS_SELECTOR, "ul")
        if uls:
            largest_ul = max(uls, key=lambda x: len(x.text))
            logger.info(f"<ul> 태그 발견 (fallback): {len(uls)}개, 선택된 ul 텍스트 길이: {len(largest_ul.text)}")
            return _extract_tree_from_selenium_element(largest_ul, driver, use_dynamic)
    except Exception as e:
        logger.debug(f"<ul> 태그 찾기 실패: {e}")
    
    logger.warning("카테고리 컨테이너를 찾지 못했습니다")
    return {}


def is_valid_category_text(text: str) -> bool:
    """
    방법 2: 카테고리 텍스트 패턴 검증
    - 한글 2~10자
    - 공백 없음 or 한 번 정도
    - 숫자 없음
    - 특수문자 없음
    - 반복되지 않음
    """
    if not text or len(text) < 2 or len(text) > 10:
        return False
    
    # 공백 체크 (0개 또는 1개만 허용)
    space_count = text.count(' ')
    if space_count > 1:
        return False
    
    # 숫자 체크 (숫자 없어야 함)
    if re.search(r'\d', text):
        return False
    
    # 특수문자 체크 (한글, 영문, 공백만 허용)
    if not re.match(r'^[가-힣a-zA-Z\s]+$', text):
        return False
    
    # 반복 체크 (같은 글자 3번 이상 반복 없음)
    for char in text:
        if text.count(char) >= 3:
            return False
    
    # 동사 체크 (간단한 동사 어미 제외)
    verb_endings = ['하다', '되다', '이다', '있다', '없다']
    if any(text.endswith(ending) for ending in verb_endings):
        return False
    
    return True


def _extract_tree_from_selenium_element(
    element: WebElement,
    driver: webdriver.Chrome,
    use_dynamic: bool = True,
    depth: int = 0,
    max_depth: int = 3
) -> Dict[str, Dict]:
    """
    Selenium WebElement에서 카테고리 트리 추출 (재귀)
    
    Args:
        element: Selenium WebElement
        driver: Selenium WebDriver
        use_dynamic: 동적 submenu 추출 사용 여부
        depth: 현재 깊이
        max_depth: 최대 깊이
    """
    if depth >= max_depth:
        return {}
    
    tree = {}
    
    try:
        # 직계 자식 요소 찾기 (여러 방법 시도)
        children = []
        
        # 방법 1: XPath로 직계 자식 찾기
        try:
            children = element.find_elements(By.XPATH, "./*")  # 모든 직계 자식
            # li, div, a만 필터링
            children = [c for c in children if c.tag_name.lower() in ['li', 'div', 'a']]
        except:
            pass
        
        # 방법 2: CSS Selector로 찾기 (XPath 실패 시)
        if not children:
            try:
                children = element.find_elements(By.CSS_SELECTOR, "> li, > div, > a")
            except:
                pass
        
        # 방법 3: JavaScript로 직접 찾기 (fallback)
        if not children:
            try:
                children = driver.execute_script(
                    "return Array.from(arguments[0].children).filter("
                    "  el => ['LI', 'DIV', 'A'].includes(el.tagName)"
                    ");",
                    element
                )
            except:
                pass
        
        logger.info(f"직계 자식 요소: {len(children)}개 (depth: {depth})")
        
        # 속도 최적화: 상위 5개만 동적 분석 수행
        text_extracted_count = 0
        
        # 직계 자식이 적으면 (5개 미만) 더 깊이 탐색 시도
        if len(children) < 5 and depth == 0:
            logger.info("직계 자식이 적어서 더 깊이 탐색 시도...")
            # li 요소를 직접 찾기 (직계가 아니어도)
            try:
                li_elements = element.find_elements(By.CSS_SELECTOR, "li")
                if len(li_elements) > len(children):
                    logger.info(f"li 요소 발견: {len(li_elements)}개 (직계 자식 대신 사용)")
                    children = li_elements[:50]  # 상위 50개만 (성능 고려)
            except:
                pass
        
        # 디버깅: 자식 요소 태그 정보
        if children:
            tag_counts = {}
            for child in children[:10]:  # 처음 10개만
                tag = child.tag_name.lower()
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            logger.debug(f"자식 요소 태그 분포 (상위 10개): {tag_counts}")
        
        for child in children:
            try:
                # 방법 3: Selenium으로만 카테고리 찾기 (텍스트 추출 개선)
                # <a> 태그의 텍스트만 추출 (직접 텍스트 노드)
                text = None
                try:
                    # <a> 태그가 있으면 <a>의 직접 텍스트만 추출
                    link = child.find_element(By.CSS_SELECTOR, "a")
                    if link:
                        # JavaScript로 직접 텍스트 노드만 가져오기
                        text = driver.execute_script(
                            "return arguments[0].childNodes[0] ? arguments[0].childNodes[0].textContent.trim() : arguments[0].textContent.trim();",
                            link
                        )
                        if not text or len(text) == 0:
                            # fallback: 일반 text 속성 사용
                            text = link.text.strip()
                except:
                    pass
                
                # <a> 태그가 없으면 직접 텍스트 노드 추출
                if not text:
                    try:
                        # JavaScript로 직접 텍스트 노드만 가져오기
                        text = driver.execute_script(
                            "var nodes = arguments[0].childNodes;"
                            "for (var i = 0; i < nodes.length; i++) {"
                            "  if (nodes[i].nodeType === 3) {"
                            "    return nodes[i].textContent.trim();"
                            "  }"
                            "}"
                            "return arguments[0].textContent.trim();",
                            child
                        )
                    except:
                        # fallback: 일반 text 속성 사용
                        text = child.text.strip()
                
                # 공백 제거 및 정리
                if text:
                    text = text.strip()
                    # 여러 공백을 하나로
                    text = re.sub(r'\s+', ' ', text)
                
                logger.debug(f"[CSR] child 태그={child.tag_name}, 텍스트='{text[:50] if text else 'None'}', 길이={len(text) if text else 0}")
                
                # 방법 2: 카테고리 텍스트 패턴 검증
                if not text or not is_valid_category_text(text):
                    logger.debug(f"[CSR] 텍스트 패턴 검증 실패: '{text[:30] if text else 'None'}'")
                    continue
                
                # 중복 제거
                if text in tree:
                    continue
                
                logger.info(f"[CSR] 텍스트 추출 성공: '{text}' (태그={child.tag_name})")
                text_extracted_count += 1
                
                # 추가 정보 수집 (디버깅용)
                try:
                    href = None
                    try:
                        link_elem = child.find_element(By.CSS_SELECTOR, "a")
                        if link_elem:
                            href = link_elem.get_attribute("href")
                    except:
                        pass
                    classes = child.get_attribute("class") or ""
                    element_id = child.get_attribute("id") or ""
                    logger.debug(f"[CSR] 상세 정보 - href={href}, class={classes}, id={element_id}")
                except:
                    pass
                
                # 하위 메뉴 확인 (동적) - 속도 최적화: 상위 5개만 동적 분석
                if use_dynamic and text_extracted_count <= 5:
                    try:
                        # hover/click 기반 판별
                        menu_behavior = detect_menu_behavior(
                            driver=driver,
                            selenium_element=child,
                            use_dynamic=True
                        )
                        
                        logger.debug(f"카테고리 '{text}' 동작 방식: {menu_behavior}")
                        
                        # 판별된 방식에 따라 처리
                        if menu_behavior == "hover":
                            # hover만 시도
                            from scraper.category_interaction import hover_element, hover_and_wait_for_submenu
                            hover_success = hover_element(driver, child, wait_seconds=0.3)
                            if hover_success:
                                submenu_opened = hover_and_wait_for_submenu(driver, child, timeout=2.0)
                                if submenu_opened:
                                    submenu = _find_opened_submenu(child, driver)
                                    if submenu:
                                        sub_tree = _extract_tree_from_selenium_element(
                                            submenu, driver, use_dynamic, depth + 1, max_depth
                                        )
                                        if sub_tree:
                                            tree[text] = sub_tree
                                            continue
                        elif menu_behavior == "click":
                            # click만 시도
                            try:
                                child.click()
                                time.sleep(0.5)
                                submenu = _find_opened_submenu(child, driver)
                                if submenu:
                                    sub_tree = _extract_tree_from_selenium_element(
                                        submenu, driver, use_dynamic, depth + 1, max_depth
                                    )
                                    if sub_tree:
                                        tree[text] = sub_tree
                                        continue
                            except:
                                pass
                        else:
                            # unknown이면 기존 fallback 방식 사용
                            success, method = click_category_with_fallback(
                                driver, child, timeout=2.0
                            )
                            if success:
                                time.sleep(0.5)  # submenu 렌더링 대기
                                submenu = _find_opened_submenu(child, driver)
                                if submenu:
                                    sub_tree = _extract_tree_from_selenium_element(
                                        submenu, driver, use_dynamic, depth + 1, max_depth
                                    )
                                    if sub_tree:
                                        tree[text] = sub_tree
                                        continue
                    except Exception as e:
                        logger.debug(f"동적 submenu 추출 실패 ({text}): {e}")
                
                # 하위 구조가 없음 → leaf node
                tree[text] = {}
                
            except Exception as e:
                logger.debug(f"요소 처리 중 오류: {e}")
                continue
        
    except Exception as e:
        logger.debug(f"트리 추출 중 오류: {e}")
    
    return tree


def detect_hover_needed_from_element(element: WebElement) -> bool:
    """
    Selenium WebElement가 hover가 필요한지 확인
    """
    try:
        # aria-haspopup, aria-expanded 속성 확인
        aria_haspopup = element.get_attribute("aria-haspopup")
        aria_expanded = element.get_attribute("aria-expanded")
        
        if aria_haspopup == "true" or aria_expanded is not None:
            return True
        
        # class 확인
        classes = element.get_attribute("class") or ""
        hover_keywords = ["submenu", "dropdown", "has-submenu", "has-children"]
        if any(kw in classes.lower() for kw in hover_keywords):
            return True
        
        # data 속성 확인
        data_toggle = element.get_attribute("data-toggle")
        if data_toggle == "dropdown":
            return True
        
        return False
    except:
        return False


def _find_opened_submenu(
    element: WebElement,
    driver: webdriver.Chrome
) -> Optional[WebElement]:
    """
    열린 submenu 찾기
    """
    try:
        # SUBMENU_SELECTORS로 찾기
        for selector in SUBMENU_SELECTORS:
            try:
                # 요소 내부에서 찾기
                submenu = element.find_element(By.CSS_SELECTOR, selector)
                if submenu.is_displayed():
                    return submenu
            except:
                continue
            
            # 부모 요소에서 찾기
            try:
                parent = driver.execute_script("return arguments[0].parentElement;", element)
                if parent:
                    submenu = parent.find_element(By.CSS_SELECTOR, selector)
                    if submenu.is_displayed():
                        return submenu
            except:
                continue
        
        # 형제 요소에서 찾기
        try:
            sibling = element.find_element(By.XPATH, "./following-sibling::*[1]")
            if sibling.is_displayed():
                tag_name = sibling.tag_name.lower()
                if tag_name in ["ul", "div"]:
                    return sibling
        except:
            pass
        
    except Exception as e:
        logger.debug(f"submenu 찾기 실패: {e}")
    
    return None
