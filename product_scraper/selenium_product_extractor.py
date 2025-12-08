"""
단순 Selenium 기반 상품 정보 추출기.
페이지가 GPT로 잘 안 풀릴 때 최소한의 상품명/가격/브랜드를 셀레니움으로 가져옵니다.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Optional, Dict

from bs4 import BeautifulSoup

from keywordCrawler.keywordCrawler.infra.driver_factory import DriverFactory

logger = logging.getLogger(__name__)


@dataclass
class SeleniumProductDetail:
    name: Optional[str] = None
    price: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "name": self.name,
            "price": self.price,
            "brand": self.brand,
            "description": self.description,
            "image_url": self.image_url,
        }


class SeleniumProductExtractor:
    """
    Selenium + BeautifulSoup 조합으로 상품 정보를 추출합니다.
    - 단일 페이지 기준, 간단한 CSS 선택자만 사용
    - 사이트별 세밀한 대응은 필요에 따라 추가해야 합니다.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_product_info(self, product_url: str, wait_seconds: int = 8) -> SeleniumProductDetail:
        """상품 URL에서 이름/가격/브랜드를 추출."""
        self.logger.info(f"🔍 Selenium 상품 추출 시작: {product_url}")

        driver = None
        try:
            factory = DriverFactory(headless=self.headless)
            driver = factory.create()
            driver.get(product_url)

            # 기본 대기 + 간단 스크롤로 lazy-load 유도
            time.sleep(wait_seconds)
            driver.execute_script("window.scrollTo(0, 1200);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            name = self._extract_name(soup)
            price = self._extract_price(soup)
            brand = self._extract_brand(soup)
            description = self._extract_description(soup)
            image_url = self._extract_image(soup)

            detail = SeleniumProductDetail(
                name=name,
                price=price,
                brand=brand,
                description=description,
                image_url=image_url,
            )

            self.logger.info(f"✅ Selenium 추출 완료: {detail.to_dict()}")
            return detail
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    self.logger.warning("드라이버 종료 중 오류: %s", e)

    # --- 개별 필드 추출기 ---

    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        # 대표적으로 og:title, h1, 상품명 클래스 등을 시도
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        for selector in [
            "h1",
            "h2",
            ".product_title",
            ".product-name",
            ".prodName",
            ".title",
            ".product-right-section .text-lookup",  # KREAM
        ]:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        # 메타 태그 우선 (opengraph/product schema)
        meta_props = [
            ("meta", {"property": "product:price:amount"}),
            ("meta", {"property": "og:price:amount"}),
            ("meta", {"property": "product:price"}),
            ("meta", {"name": "price"}),
            ("meta", {"itemprop": "price"}),
        ]
        for tag, attrs in meta_props:
            el = soup.find(tag, attrs=attrs)
            if el and el.get("content"):
                return el["content"].strip()

        for selector in [
            ".price",
            ".sale-price",
            ".product-price",
            ".price-info-container .bold",  # KREAM 현재가
            ".price-info-container .text-lookup",  # KREAM 발매가/가격 텍스트
            ".prodPrice",
            ".priceArea",
            ".GoodsDetailInfo_price__AoTh8",         # oliveyoung
            ".price_wrap"       # EQL
        ]:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        # 메타 태그 우선
        meta_props = [
            ("meta", {"property": "product:brand"}),
            ("meta", {"property": "og:brand"}),
            ("meta", {"name": "brand"}),
            ("meta", {"itemprop": "brand"}),
        ]
        for tag, attrs in meta_props:
            el = soup.find(tag, attrs=attrs)
            if el and el.get("content"):
                return el["content"].strip()

        for selector in [
            ".brand",
            ".brand-name",
            ".brandName",
            ".product-brand",
            ".brandNameArea",
            ".TopUtils_btn-brand__tvEdp",    # oliveyoung
        ]:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in [
            "meta[name='description']",
            ".product-description",
            ".prodDescription",
        ]:
            el = soup.select_one(selector)
            if not el:
                continue
            if el.name == "meta" and el.get("content"):
                return el["content"].strip()
            if el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            return og_img["content"].strip()
        first_img = soup.find("img", src=True)
        if first_img:
            return first_img["src"]
        return None
