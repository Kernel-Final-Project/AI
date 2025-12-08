"""
URL 정제 로직
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from .url_patterns import find_pattern_by_url, URLPattern, SHOPPING_PATTERNS

logger = logging.getLogger(__name__)


class UnsupportedShoppingMallError(Exception):
    """지원되지 않는 쇼핑몰 에러"""
    pass


@dataclass
class RefineResult:
    """URL 정제 결과"""
    original_url: str
    keyword: str
    refined_url: str
    shopping_mall: str
    pattern_used: Optional[URLPattern] = None

    def to_dict(self):
        return {
            "original_url": self.original_url,
            "keyword": self.keyword,
            "refined_url": self.refined_url,
            "shopping_mall": self.shopping_mall,
        }


class URLRefiner:
    """URL 정제기"""

    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: True면 지원되지 않는 쇼핑몰에서 예외 발생,
                        False면 경고만 출력하고 계속 진행
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(self.__class__.__name__)

    def refine(self, base_url: str, keyword: str) -> RefineResult:
        """
        메인 URL + 키워드 -> 검색 URL 생성
        
        Args:
            base_url: 쇼핑몰 메인 URL (예: https://www.musinsa.com)
            keyword: 검색 키워드 (예: 기모후드집업)
        
        Returns:
            RefineResult: 정제된 URL 정보
        
        Raises:
            UnsupportedShoppingMallError: strict_mode=True이고 지원되지 않는 쇼핑몰인 경우
        """
        self.logger.info(f"🔧 URL 정제 시작: {base_url} + '{keyword}'")

        # URL 파싱
        parsed = urlparse(base_url)
        domain = parsed.netloc or parsed.path  # netloc이 없으면 path 사용

        # 쇼핑몰 패턴 찾기
        pattern = find_pattern_by_url(base_url)

        if not pattern:
            # 지원되지 않는 쇼핑몰
            return self._handle_unsupported_mall(base_url, keyword, domain)

        # 패턴을 사용해서 검색 URL 생성
        refined_url = pattern.build_search_url(keyword)
        shopping_mall = pattern.name
        self.logger.info(f"✅ {shopping_mall} 패턴 사용")

        result = RefineResult(
            original_url=base_url,
            keyword=keyword,
            refined_url=refined_url,
            shopping_mall=shopping_mall,
            pattern_used=pattern
        )

        self.logger.info(f"🎯 정제 완료: {refined_url}")
        return result

    def _handle_unsupported_mall(self, base_url: str, keyword: str, domain: str) -> RefineResult:
        """지원되지 않는 쇼핑몰 처리"""

        # 지원되는 쇼핑몰 목록 생성
        supported_malls = [p.name for p in SHOPPING_PATTERNS]
        supported_domains = [p.domain for p in SHOPPING_PATTERNS]

        error_message = (
            f"❌ 지원되지 않는 쇼핑몰: {domain}\n\n"
            f"현재 지원되는 쇼핑몰:\n"
            + "\n".join([f"  - {name} ({domain})" for name, domain in zip(supported_malls, supported_domains)])
        )

        self.logger.error(error_message)

        if self.strict_mode:
            # strict 모드: 예외 발생
            raise UnsupportedShoppingMallError(error_message)
        else:
            # 비strict 모드: 경고만 출력하고 임시 URL 생성
            self.logger.warning("⚠️  비strict 모드로 임시 URL 생성 시도")
            refined_url = self._build_generic_search_url(base_url, keyword)

            return RefineResult(
                original_url=base_url,
                keyword=keyword,
                refined_url=refined_url,
                shopping_mall=f"미지원 ({domain})",
                pattern_used=None
            )

    def _build_generic_search_url(self, base_url: str, keyword: str) -> str:
        """
        범용 검색 URL 생성 (패턴이 없을 때)
        ⚠️ 주의: 이 방법은 대부분의 쇼핑몰에서 작동하지 않을 수 있습니다
        """
        from urllib.parse import quote

        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else base_url

        if not base.endswith('/'):
            base += '/'

        encoded_keyword = quote(keyword)
        return f"{base}search?q={encoded_keyword}"

    @staticmethod
    def get_supported_malls() -> list[dict]:
        """
        지원되는 쇼핑몰 목록 반환
        
        Returns:
            list[dict]: 쇼핑몰 정보 리스트
        """
        return [
            {
                "name": p.name,
                "domain": p.domain,
                "example_url": f"https://{p.domain}"
            }
            for p in SHOPPING_PATTERNS
        ]

