"""
상품 크롤링 모듈
XPath 기반
"""

from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from musinsa_parser.config import BASE_URL
from musinsa_parser.category_crawler import (
    build_top_categories,
    click_1depth_and_get_2depth,
)


def extract_product_name(card_container):
    """
    무신사 상품명 확보 (카드 컨테이너에서 Typography span 수집)
    """
    # 1) aria-label 우선 시도 (a 태그에서)
    try:
        a_tag = card_container.find_element(By.XPATH, ".//a[@data-item-id]")
        aria = a_tag.get_attribute("aria-label")
        if aria:
            name = aria.replace("상품상세로 이동", "").replace("상품 상세로 이동", "").strip()
            if name and len(name) > 4:
                return name
    except:
        pass

    # 2) 카드 컨테이너 내부의 모든 Typography span 찾기
    try:
        spans = card_container.find_elements(By.XPATH, ".//span[@data-mds='Typography']")
        
        texts = [s.text.strip() for s in spans if s.text.strip()]
        
        # 가격(원, %), 페이지 전체 텍스트(결산, 빅세일) 제외 → 상품명만 추출
        name_candidates = [
            t for t in texts
            if ("원" not in t and "%" not in t 
                and "결산" not in t and "빅세일" not in t
                and len(t) > 2 and len(t) < 200)  # 너무 긴 텍스트 제외
        ]
        
        if name_candidates:
            # 가장 긴 텍스트를 상품명으로 선택 (브랜드명보다 상품명이 더 길기 때문)
            return max(name_candidates, key=len)
    except Exception as e:
        logger.debug(f"상품명 추출 중 오류: {e}")

    return "N/A"


def crawl_category_page(
    driver: webdriver.Chrome, category_url: str, max_products: int = 100
) -> List[Dict[str, str]]:
    """
    카테고리 페이지에서 상품 크롤링

    Args:
        driver: Selenium WebDriver
        category_url: 카테고리 페이지 URL
        max_products: 최대 수집할 상품 개수

    Returns:
        상품 정보 리스트
    """
    try:
        logger.info(f"카테고리 페이지 크롤링 시작: {category_url}")

        driver.get(category_url)
        time.sleep(2)

        # XPath로 직접 상품 추출
        products = extract_products_xpath(driver, max_products)

        logger.info(f"크롤링 완료: {len(products)}개 상품 수집")
        return products

    except Exception as e:
        logger.error(f"카테고리 페이지 크롤링 중 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return []


def extract_products_xpath(
    driver: webdriver.Chrome, limit: int = 10
) -> List[Dict[str, str]]:
    """
    XPath 기반으로 상품 정보 추출

    Args:
        driver: Selenium WebDriver
        limit: 추출할 상품 개수

    Returns:
        상품 정보 리스트
    """
    wait = WebDriverWait(driver, 10)

    # 카드 전체 요소 잡기 (a 태그의 조상 요소 중 3번째 div)
    cards = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[contains(@class, 'sc')]//a[@data-item-id]/ancestor::div[3]")
        )
    )

    results = []
    seen = set()

    for card_container in cards[:limit]:
        try:
            # 카드 컨테이너 내부의 a 태그 찾기
            try:
                card = card_container.find_element(By.XPATH, ".//a[@data-item-id]")
            except:
                continue
            
            # 상품코드
            product_code = card.get_attribute("data-item-id")
            if not product_code or product_code in seen:
                continue
            seen.add(product_code)

            # URL
            url = card.get_attribute("href")
            if url and not url.startswith("http"):
                url = f"https://www.musinsa.com{url}"

            # 상품명 추출 (카드 컨테이너에서 찾기)
            product_name = extract_product_name(card_container)

            # 가격 (data-best-price 우선)
            best = card.get_attribute("data-best-price")
            orig = card.get_attribute("data-original-price")
            raw_price = best or orig
            if raw_price:
                product_price = f"{int(raw_price):,}원"
            else:
                product_price = "N/A"

            # 이미지 (카드 컨테이너에서 찾기)
            try:
                img_elem = card_container.find_element(By.XPATH, ".//img[@data-mds='Image']")
                image_url = img_elem.get_attribute("src")
            except:
                image_url = "N/A"

            results.append(
                {
                    "product_code": product_code,
                    "product_name": product_name,
                    "product_price": product_price,
                    "image_url": image_url,
                    "product_url": url,
                }
            )

            logger.info(f"상품: {product_name} | {product_price} | {product_code}")

        except Exception as e:
            logger.warning(f"상품 파싱 실패: {e}")
            continue

    return results


def crawl_from_main(
    category_path: List[str], max_products: int = 100
) -> List[Dict[str, str]]:
    """
    메인 페이지에서 시작하여 카테고리로 이동 후 크롤링

    Args:
        category_path: 카테고리 경로 리스트 (예: ["뷰티", "스킨케어"])
        max_products: 최대 수집할 상품 개수

    Returns:
        상품 정보 리스트
    """
    category_path_str = " > ".join(category_path)
    logger.info(f"카테고리 경로 '{category_path_str}' 크롤링 시작")

    driver = None
    try:
        driver = setup_browser(headless=False)

        # 1depth 클릭 및 2depth 목록 가져오기
        if len(category_path) >= 2:
            _1depth_name = category_path[0]
            _2depth_name = category_path[1]

            # 1depth 카테고리 ID를 찾기 위해 build_top_categories 호출
            top_categories = build_top_categories(driver)
            _1depth_node = next(
                (
                    node
                    for node in top_categories
                    if node.name == _1depth_name and node.depth == 1
                ),
                None,
            )

            if not _1depth_node:
                logger.error(f"1depth 카테고리 '{_1depth_name}'를 찾을 수 없습니다.")
                return []

            # 1depth 클릭 후 2depth 목록 가져오기
            depth2_categories = click_1depth_and_get_2depth(
                driver, _1depth_node.category_id
            )

            _2depth_node = next(
                (
                    node
                    for node in depth2_categories
                    if node.name == _2depth_name and node.depth == 2
                ),
                None,
            )

            if not _2depth_node or not _2depth_node.url:
                logger.error(
                    f"2depth 카테고리 '{_2depth_name}'를 찾을 수 없거나 URL이 없습니다."
                )
                return []

            category_url = _2depth_node.url
        else:
            logger.error(
                "최소 2depth 카테고리 경로가 필요합니다 (예: ['뷰티', '스킨케어'])"
            )
            return []

        # 2depth 카테고리 페이지로 이동
        driver.get(category_url)
        time.sleep(2)  # 페이지 로드 대기

        # 상품 추출
        return extract_products_xpath(driver, max_products)

    except Exception as e:
        logger.error(f"크롤링 중 오류: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return []
    finally:
        if driver:
            driver.quit()
            logger.info("브라우저 종료")
