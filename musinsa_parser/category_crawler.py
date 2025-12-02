"""
카테고리 탐지 및 크롤링 모듈
XPath 기반
"""

from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import re

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from musinsa_parser.config import (
    BASE_URL,
    XPATH_CATEGORY_BUTTON,
    XPATH_TOP_CATEGORY_ITEMS,
    XPATH_SUBCATEGORY_ITEMS_REL,
)
from musinsa_parser.category_node import CategoryNode


def open_musinsa_category_panel(driver):
    driver.get(BASE_URL)
    logger.info(f"무신사 메인 접속: {BASE_URL}")

    wait = WebDriverWait(driver, 10)

    # 1) 카테고리 버튼 클릭
    button = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_CATEGORY_BUTTON)))
    logger.info("카테고리 버튼 발견, 클릭")
    button.click()
    time.sleep(0.5)  # Shadow DOM 생성 대기

    # 2) Shadow DOM 감지 및 카테고리 추출 시도
    time.sleep(1)  # 패널이 완전히 열릴 때까지 대기
    
    data = driver.execute_script(
        """
        const btn = document.querySelector('[data-button-id="category_menu"]');
        if (!btn) return {type: 'error', message: '버튼을 찾을 수 없음'};
        
        // Shadow DOM 확인
        if (btn.shadowRoot) {
            const items = btn.shadowRoot.querySelectorAll('[data-button-id="1depth_cate"]');
            if (items.length > 0) {
                return {
                    type: 'shadow',
                    items: Array.from(items).map(el => ({
                        name: el.textContent.trim(),
                        url: el.getAttribute('href'),
                        category_id: el.getAttribute('data-category-id')
                    }))
                };
            }
        }
        
        // 일반 DOM에서 시도 - 1depth만 추출
        const nav = document.querySelector('nav[class*="CategoryMenu"]');
        if (nav) {
            // 1depth는 보통 첫 번째 ul의 직접 자식 li에 있음
            const firstUl = nav.querySelector('ul');
            if (firstUl) {
                const items = firstUl.querySelectorAll(':scope > li > a[data-category-id]');
                if (items.length > 0) {
                    return {
                        type: 'normal',
                        items: Array.from(items).map(el => ({
                            name: el.textContent.trim(),
                            url: el.getAttribute('href'),
                            category_id: el.getAttribute('data-category-id')
                        }))
                    };
                }
            }
            
            // fallback: 모든 a 태그에서 URL 패턴으로 필터링
            const allItems = nav.querySelectorAll('a[data-category-id]');
            const filtered = Array.from(allItems).filter(el => {
                const href = el.getAttribute('href') || '';
                // 1depth는 보통 /category/001 형식 (3자리 숫자)
                return /\/category\/\d{3}$/.test(href);
            });
            
            if (filtered.length > 0) {
                return {
                    type: 'normal',
                    items: filtered.map(el => ({
                        name: el.textContent.trim(),
                        url: el.getAttribute('href'),
                        category_id: el.getAttribute('data-category-id')
                    }))
                };
            }
        }
        
        // 다른 선택자 시도 - 1depth만
        const divItems = document.querySelectorAll('div[data-button-id="1depth_cate"]');
        if (divItems.length > 0) {
            return {
                type: 'div',
                items: Array.from(divItems).map(el => ({
                    name: el.textContent.trim(),
                    url: el.getAttribute('href') || el.querySelector('a')?.getAttribute('href'),
                    category_id: el.getAttribute('data-category-id')
                }))
            };
        }
        
        return {type: 'error', message: '카테고리 요소를 찾을 수 없음'};
        """
    )
    
    if data and data.get('type') in ['shadow', 'normal', 'div']:
        items = data.get('items', [])
        logger.info(f"{data['type']} DOM에서 카테고리 {len(items)}개 추출")
        return items

    # 3) 최종 fallback - 여러 XPath 시도
    logger.warning("JavaScript로 카테고리 추출 실패, XPath로 재시도")
    
    # 여러 XPath 패턴 시도
    xpath_patterns = [
        XPATH_TOP_CATEGORY_ITEMS,
        "//p[@data-button-id='1depth_cate']",  # 1depth 메인 카테고리 (<p> 태그)
        "//div[@data-button-id='1depth_cate']",
        "//*[@data-button-id='1depth_cate']",  # 모든 태그에서 1depth 찾기
        "//nav//a[@data-category-id]",
        "//div[contains(@class, 'CategoryMenu')]//a",
    ]
    
    for xpath in xpath_patterns:
        try:
            top_items = wait.until(
                EC.presence_of_all_elements_located((By.XPATH, xpath))
            )
            if top_items:
                logger.info(f"XPath로 카테고리 {len(top_items)}개 발견: {xpath}")
                return top_items
        except:
            continue
    
    logger.error("모든 방법으로 카테고리 요소를 찾을 수 없습니다")
    return []


def build_top_categories(driver) -> List[CategoryNode]:
    """
    1depth 카테고리 (상의, 아우터, 바지, 스니커즈…)를 CategoryNode 리스트로 변환

    Args:
        driver: Selenium WebDriver

    Returns:
        CategoryNode 리스트
    """
    top_elements = open_musinsa_category_panel(driver)
    nodes: List[CategoryNode] = []

    # Shadow DOM에서 추출한 딕셔너리 데이터인지 확인
    if top_elements and isinstance(top_elements, list) and len(top_elements) > 0:
        if isinstance(top_elements[0], dict):
            # Shadow DOM에서 추출한 데이터 처리
            for data in top_elements:
                try:
                    name = (data.get("name") or "").strip()

                    # 빈 이름이나 필터링 대상 제외
                    if not name or name in ["전체", "남성", "여성", "전체 보기"]:
                        continue

                    # category_id 추출
                    category_id = data.get("category_id")
                    
                    # URL 추출
                    url = data.get("url")
                    
                    # depth 판별
                    # 2depth: URL에서 6자리 숫자만 찾기 (우선 확인)
                    # 1depth: data-category-id가 3자리 숫자 (2depth가 아닐 때만)
                    depth = 0
                    
                    # 2depth 판별: URL에서 6자리 숫자만 찾기 (3자리는 무시)
                    if url:
                        # 브랜드 필터링 링크 제외 (쿼리 파라미터가 있으면 제외)
                        if '?' in url and ('brandLineUp' in url or 'separatorId' in url):
                            continue
                        
                        match = re.search(r'/category/(\d{6})', url)
                        if match:
                            depth = 2
                        # 1depth 판별: 6자리 숫자가 없고, category_id가 3자리 숫자면 1depth
                        elif category_id and re.match(r'^\d{3}$', category_id):
                            depth = 1
                        else:
                            # 둘 다 아니면 제외
                            continue
                    elif category_id and re.match(r'^\d{3}$', category_id):
                        # URL이 없어도 category_id가 3자리면 1depth
                        depth = 1
                    else:
                        continue
                    
                    if url and not url.startswith("http"):
                        url = f"https://www.musinsa.com{url}"

                    # XPath 생성
                    if category_id:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
                    else:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-button-name='{name}']"

                    # node_type 결정
                    if depth == 1:
                        node_type = "main"
                    elif depth == 2:
                        node_type = "sub"
                    elif depth >= 3:
                        node_type = "leaf"
                    else:
                        node_type = "unknown"
                    
                    node = CategoryNode(
                        name=name,
                        url=url,
                        xpath=xpath,
                        category_id=category_id,
                        node_type=node_type,
                        depth=depth,
                    )

                    nodes.append(node)
                    logger.info(
                        f"{depth}depth 카테고리 발견 ({node_type}): {name} | url={url} | id={category_id}"
                    )

                except Exception as e:
                    logger.warning(f"카테고리 데이터 처리 중 오류: {e}")
                    continue
        else:
            # 일반 DOM에서 추출한 WebElement 처리
            for el in top_elements:
                try:
                    name = (el.text or "").strip()

                    # 빈 이름이나 필터링 대상 제외
                    if not name or name in ["전체", "남성", "여성", "전체 보기"]:
                        continue

                    # category_id 추출
                    category_id = el.get_attribute("data-category-id")
                    
                    # URL 추출 (<p> 태그는 href가 없을 수 있으므로 여러 속성 확인)
                    url = el.get_attribute("href") or el.get_attribute("data-href") or None
                    
                    # depth 판별
                    # 2depth: URL에서 6자리 숫자만 찾기 (우선 확인)
                    # 1depth: data-category-id가 3자리 숫자 (2depth가 아닐 때만)
                    depth = 0
                    
                    # 2depth 판별: URL에서 6자리 숫자만 찾기 (3자리는 무시)
                    if url:
                        # 브랜드 필터링 링크 제외 (쿼리 파라미터가 있으면 제외)
                        if '?' in url and ('brandLineUp' in url or 'separatorId' in url):
                            continue
                        
                        match = re.search(r'/category/(\d{6})', url)
                        if match:
                            depth = 2
                        # 1depth 판별: 6자리 숫자가 없고, category_id가 3자리 숫자면 1depth
                        elif category_id and re.match(r'^\d{3}$', category_id):
                            depth = 1
                        else:
                            # 둘 다 아니면 제외
                            continue
                    elif category_id and re.match(r'^\d{3}$', category_id):
                        # URL이 없어도 category_id가 3자리면 1depth
                        depth = 1
                    else:
                        continue
                    
                    if url and not url.startswith("http"):
                        url = f"https://www.musinsa.com{url}"

                    # XPath 생성
                    if category_id:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
                    else:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-button-name='{name}']"

                    # node_type 결정
                    if depth == 1:
                        node_type = "main"
                    elif depth == 2:
                        node_type = "sub"
                    elif depth >= 3:
                        node_type = "leaf"
                    else:
                        node_type = "unknown"
                    
                    node = CategoryNode(
                        name=name,
                        url=url,
                        xpath=xpath,
                        category_id=category_id,
                        node_type=node_type,
                        depth=depth,
                    )

                    nodes.append(node)
                    logger.info(
                        f"{depth}depth 카테고리 발견 ({node_type}): {name} | url={url} | id={category_id}"
                    )

                except Exception as e:
                    logger.warning(f"카테고리 요소 처리 중 오류: {e}")
                    continue

    return nodes


def click_1depth_and_get_2depth(driver, category_id: str) -> List[CategoryNode]:
    """
    1depth 카테고리 클릭 후 2depth 목록 가져오기
    
    Args:
        driver: Selenium WebDriver
        category_id: 1depth 카테고리 ID (예: "104")
        
    Returns:
        2depth 카테고리 CategoryNode 리스트
    """
    wait = WebDriverWait(driver, 10)
    
    # 카테고리 패널 열기
    open_musinsa_category_panel(driver)
    time.sleep(1)
    
    # 1depth 카테고리 클릭
    try:
        # p 태그로 된 1depth 클릭
        xpath_1depth = f"//p[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_1depth)))
        logger.info(f"1depth 카테고리 클릭: category_id={category_id}")
        element.click()
        time.sleep(1.5)  # 2depth 표시 대기
    except:
        # div 태그로 시도
        try:
            xpath_1depth = f"//div[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_1depth)))
            logger.info(f"1depth 카테고리 클릭 (div): category_id={category_id}")
            element.click()
            time.sleep(1.5)
        except Exception as e:
            logger.error(f"1depth 카테고리 클릭 실패: {e}")
            return []
    
    # 2depth 카테고리 목록 가져오기 (현재 패널에서 직접 찾기)
    nodes: List[CategoryNode] = []
    
    try:
        # 2depth 카테고리 링크 찾기 (a 태그, URL에 6자리 숫자)
        # category_id로 시작하는 6자리 숫자 패턴 (예: 104001, 104002)
        xpath_2depth = f"//a[contains(@href, '/category/{category_id}')]"
        depth2_elements = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, xpath_2depth))
        )
        
        for el in depth2_elements:
            try:
                url = el.get_attribute("href")
                if not url:
                    continue
                
                # 6자리 숫자 확인 (2depth)
                match = re.search(r'/category/(\d{6})', url)
                if not match:
                    continue
                
                # 브랜드 필터링 링크 제외
                if '?' in url and ('brandLineUp' in url or 'separatorId' in url):
                    continue
                
                name = (el.text or "").strip()
                if not name:
                    continue
                
                category_id_2depth = el.get_attribute("data-category-id")
                
                if url and not url.startswith("http"):
                    url = f"https://www.musinsa.com{url}"
                
                node = CategoryNode(
                    name=name,
                    url=url,
                    category_id=category_id_2depth or category_id,
                    node_type="sub",
                    depth=2,
                )
                
                nodes.append(node)
                logger.info(f"2depth 카테고리 발견: {name} | url={url}")
                
            except Exception as e:
                logger.warning(f"2depth 카테고리 처리 중 오류: {e}")
                continue
        
    except Exception as e:
        logger.warning(f"2depth 카테고리 찾기 실패: {e}")
    
    logger.info(f"2depth 카테고리 {len(nodes)}개 발견")
    return nodes


def navigate_to_2depth_category(driver, category_url: str):
    """
    2depth 카테고리 페이지로 이동
    
    Args:
        driver: Selenium WebDriver
        category_url: 2depth 카테고리 URL
    """
    if not category_url:
        logger.error("카테고리 URL이 없습니다")
        return False
    
    if not category_url.startswith("http"):
        category_url = f"https://www.musinsa.com{category_url}"
    
    logger.info(f"2depth 카테고리 페이지로 이동: {category_url}")
    driver.get(category_url)
    time.sleep(2)  # 페이지 로드 대기
    return True
