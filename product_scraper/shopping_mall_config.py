"""
쇼핑몰별 설정 정보
- 도메인
- URL 패턴
- CSS 선택자 등
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ShoppingMallConfig:
    """쇼핑몰 설정"""
    name: str               # 쇼핑몰 이름
    domain: str             # 도메인 (검색용)
    base_url: str           # 기본 URL
    product_patterns: List[str]  # 상품 URL 패턴
    list_selector: Optional[str] = None  # 상품 리스트 CSS 선택자
    wait_time: int = 5      # 페이지 로딩 대기 시간


# 지원 쇼핑몰 설정
SHOPPING_MALLS = [
    ShoppingMallConfig(
        name="무신사",
        domain="musinsa.com",
        base_url="https://www.musinsa.com",
        product_patterns=['/products/'],
        # list_selector="li.li_box",
        wait_time=5
    ),
    ShoppingMallConfig(
        name="11번가",
        domain="11st.co.kr",
        base_url="https://www.11st.co.kr",
        product_patterns=['/products/', '/product/'],
        list_selector="div.c-card-item",
        wait_time=5
    ),
    ShoppingMallConfig(
        name="지그재그",
        domain="zigzag.kr",
        base_url="https://zigzag.kr",
        product_patterns=['/catalog/products/', '/products/'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="G마켓",
        domain="gmarket.co.kr",
        base_url="https://gmarket.co.kr",
        product_patterns=['/Item?'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="싸다구",
        domain="ssadagu.kr",
        base_url="https://ssadagu.kr/",
        product_patterns=['/shop/view.php?'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="29CM",
        domain="29cm.co.kr",
        base_url="https://product.29cm.co.kr/",
        product_patterns=['/catalog/'],
        list_selector="div[role='button']",
        wait_time=5
    ),
    ShoppingMallConfig(
        name="SSG.COM",
        domain="ssg.com",
        base_url="https://www.ssg.com/",
        product_patterns=['/item/itemView.ssg?'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="kream",
        domain="kream.co.kr",
        base_url="https://kream.co.kr",
        product_patterns=['/products/'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="oliveyoung",
        domain="oliveyoung.co.kr",
        base_url="https://www.oliveyoung.co.kr/",
        product_patterns=['/store/goods/'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="EQL",
        domain="eqlstore.com",
        base_url="https://www.eqlstore.com/",
        product_patterns=['/product/'],
        wait_time=5
    ),
    ShoppingMallConfig(
        name="coupang",
        domain="coupang.com",
        base_url="https://www.coupang.com/",
        product_patterns=['/vp/products/'],
        wait_time=5
    ),

]


class ShoppingMallManager:
    """쇼핑몰 설정 관리"""

    def __init__(self):
        self.malls = {mall.domain: mall for mall in SHOPPING_MALLS}

    def get_mall_by_domain(self, html_or_url: str) -> Optional[ShoppingMallConfig]:
        """HTML 또는 URL에서 쇼핑몰 찾기"""
        for domain, mall in self.malls.items():
            if domain in html_or_url:
                return mall
        return None

    def get_base_url(self, html_or_url: str) -> Optional[str]:
        """기본 URL 가져오기"""
        mall = self.get_mall_by_domain(html_or_url)
        return mall.base_url if mall else None

    def get_product_patterns(self, html_or_url: str) -> List[str]:
        """상품 URL 패턴 가져오기"""
        mall = self.get_mall_by_domain(html_or_url)
        return mall.product_patterns if mall else []

    def is_product_url(self, url: str) -> bool:
        """상품 URL인지 확인 (모든 쇼핑몰 패턴 검사)"""
        for mall in self.malls.values():
            for pattern in mall.product_patterns:
                if pattern in url.lower():
                    return True
        return False

    def get_supported_domains(self) -> List[str]:
        """지원되는 도메인 목록"""
        return list(self.malls.keys())
