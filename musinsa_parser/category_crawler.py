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

    # 2) Shadow DOM 감지 (정확한 위치)
    shadow_root = driver.execute_script(
        """
        const btn = document.querySelector('[data-button-id="category_menu"]');
        return btn && btn.shadowRoot ? btn.shadowRoot : null;
    """
    )

    if shadow_root:
        logger.info("Shadow DOM 내부에서 카테고리 탐색 시작")

        data = driver.execute_script(
            """
            const btn = document.querySelector('[data-button-id="category_menu"]');
            if (!btn || !btn.shadowRoot) return [];

            const items = btn.shadowRoot.querySelectorAll('[data-button-id="1depth_cate"]');

            return Array.from(items).map(el => ({
                name: el.textContent.trim(),
                url: el.getAttribute('href'),
                category_id: el.getAttribute('data-category-id')
            }));
        """
        )

        logger.info(f"Shadow DOM 카테고리 {data.length}개 추출")
        return data

    # 3) fallback
    logger.info("Shadow DOM 없음 → 일반 DOM 시도")
    top_items = wait.until(
        EC.presence_of_all_elements_located((By.XPATH, XPATH_TOP_CATEGORY_ITEMS))
    )
    return top_items


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
                    if not name or name in ["전체", "남성", "여성"]:
                        continue

                    # URL 추출
                    url = data.get("url")
                    if url and not url.startswith("http"):
                        url = f"https://www.musinsa.com{url}"

                    # category_id 추출
                    category_id = data.get("category_id")

                    # XPath 생성
                    if category_id:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
                    else:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-button-name='{name}']"

                    node = CategoryNode(
                        name=name,
                        url=url,
                        xpath=xpath,
                        category_id=category_id,
                        node_type="main",
                        depth=1,
                    )

                    nodes.append(node)
                    logger.info(
                        f"1depth 카테고리 발견 (Shadow DOM): {name} | url={url} | id={category_id}"
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
                    if not name or name in ["전체", "남성", "여성"]:
                        continue

                    # URL 추출
                    url = el.get_attribute("href")
                    if url and not url.startswith("http"):
                        url = f"https://www.musinsa.com{url}"

                    # category_id 추출
                    category_id = el.get_attribute("data-category-id")

                    # XPath 생성
                    if category_id:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-category-id='{category_id}']"
                    else:
                        xpath = f"//div[@data-button-id='1depth_cate' and @data-button-name='{name}']"

                    node = CategoryNode(
                        name=name,
                        url=url,
                        xpath=xpath,
                        category_id=category_id,
                        node_type="main",
                        depth=1,
                    )

                    nodes.append(node)
                    logger.info(
                        f"1depth 카테고리 발견: {name} | url={url} | id={category_id}"
                    )

                except Exception as e:
                    logger.warning(f"카테고리 요소 처리 중 오류: {e}")
                    continue

    return nodes
