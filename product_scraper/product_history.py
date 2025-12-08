"""
상품 히스토리 관리 (CSV 기반)
이미 작성한 상품 URL 추적
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse


logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    URL 정규화 (중복 체크용)
    - Fragment 제거
    - 쿼리 파라미터는 보존 (상품 식별자 유지: goodsNo, goodscode 등)
    - 소문자 변환
    - trailing slash 제거
    
    예:
        https://www.musinsa.com/products/123?ref=search#reviews
        -> https://www.musinsa.com/products/123?ref=search
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())

        # scheme, netloc, path + query 사용 (fragment 제거)
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),  # trailing slash 제거
            '',  # params
            parsed.query,  # query 보존 (상품 식별자 보존)
            ''   # fragment 제거
        ))

        return normalized

    except Exception as e:
        logger.warning(f"URL 정규화 실패: {url} - {e}")
        return url.strip().lower()


@dataclass
class ProductRecord:
    """상품 기록"""
    product_url: str
    keyword: Optional[str] = None
    created_at: Optional[str] = None
    product_name: Optional[str] = None

    def to_dict(self):
        return {
            "product_url": self.product_url,
            "keyword": self.keyword or "",
            "created_at": self.created_at or "",
            "product_name": self.product_name or "",
        }


class ProductHistory:
    """상품 히스토리 관리"""

    FIELDNAMES = ['product_url', 'keyword', 'created_at', 'product_name']

    def __init__(self, csv_path: str | Path = "product_list.csv"):
        """
        Args:
            csv_path: CSV 파일 경로
        """
        self.csv_path = Path(csv_path)
        self.logger = logging.getLogger(self.__class__.__name__)

        # CSV 파일 초기화
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """CSV 파일이 없으면 생성하고, 있으면 헤더 확인"""
        if not self.csv_path.exists():
            self.logger.info(f"📄 CSV 파일 생성: {self.csv_path}")
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_header()
        else:
            # 기존 파일이 있으면 헤더 확인
            self._validate_and_fix_header()

    def _write_header(self):
        """헤더 작성"""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()

    def _validate_and_fix_header(self):
        """
        기존 CSV 파일의 헤더 검증 및 수정
        헤더가 없거나 잘못되어 있으면 수정
        """
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()

            # 헤더가 없거나 잘못되어 있는지 확인
            expected_header = ','.join(self.FIELDNAMES)

            if not first_line or first_line != expected_header:
                self.logger.warning("⚠️  CSV 헤더가 없거나 잘못되었습니다. 수정 중...")
                self._fix_csv_header()
            else:
                self.logger.debug("✅ CSV 헤더 정상")

        except Exception as e:
            self.logger.error(f"헤더 검증 실패: {e}")

    def _fix_csv_header(self):
        """헤더가 없는 CSV 파일에 헤더 추가"""
        try:
            # 기존 데이터 읽기
            existing_data = []
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith('http'):  # URL로 시작하는 줄만
                        existing_data.append(line)

            # 헤더와 함께 다시 쓰기
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

                # 기존 데이터 복원
                for line in existing_data:
                    parts = line.split(',')
                    if len(parts) >= 1:
                        writer.writerow({
                            'product_url': parts[0] if len(parts) > 0 else '',
                            'keyword': parts[1] if len(parts) > 1 else '',
                            'created_at': parts[2] if len(parts) > 2 else '',
                            'product_name': parts[3] if len(parts) > 3 else '',
                        })

            self.logger.info("✅ CSV 헤더 추가 완료")

        except Exception as e:
            self.logger.error(f"CSV 헤더 수정 실패: {e}")

    def get_all_urls(self) -> Set[str]:
        """
        저장된 모든 상품 URL 반환 (정규화된 형태)
        
        Returns:
            Set[str]: 정규화된 상품 URL 집합
        """
        urls = set()

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get('product_url', '').strip()
                    if url and url.startswith('http'):
                        normalized = normalize_url(url)
                        urls.add(normalized)

            self.logger.info(f"📚 기존 상품 URL {len(urls)}개 로드됨")
            return urls

        except Exception as e:
            self.logger.warning(f"CSV 읽기 실패: {e}")
            return set()

    def is_already_used(self, product_url: str) -> bool:
        """
        URL이 이미 사용되었는지 확인 (정규화하여 비교)
        
        Args:
            product_url: 확인할 상품 URL
        
        Returns:
            bool: 이미 사용되었으면 True
        """
        normalized_input = normalize_url(product_url)
        all_urls = self.get_all_urls()

        is_used = normalized_input in all_urls

        if is_used:
            self.logger.info(f"🔄 중복 URL 발견: {product_url}")

        return is_used

    def add_product(
        self,
        product_url: str,
        keyword: Optional[str] = None,
        product_name: Optional[str] = None
    ):
        """
        새 상품 추가
        
        Args:
            product_url: 상품 URL
            keyword: 검색 키워드
            product_name: 상품명
        """
        # 중복 체크
        if self.is_already_used(product_url):
            self.logger.warning(f"⚠️  이미 존재하는 URL (중복 방지): {product_url}")
            return

        record = ProductRecord(
            product_url=product_url,
            keyword=keyword,
            created_at=datetime.now().isoformat(),
            product_name=product_name,
        )

        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writerow(record.to_dict())

            self.logger.info(f"✅ 상품 URL 추가됨: {product_url}")

        except Exception as e:
            self.logger.error(f"CSV 쓰기 실패: {e}")

    def get_all_records(self) -> List[ProductRecord]:
        """모든 레코드 반환 (디버깅용)"""
        records = []

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(ProductRecord(
                        product_url=row.get('product_url', ''),
                        keyword=row.get('keyword'),
                        created_at=row.get('created_at'),
                        product_name=row.get('product_name'),
                    ))

            return records

        except Exception as e:
            self.logger.warning(f"CSV 읽기 실패: {e}")
            return []

    def remove_duplicates(self):
        """중복 URL 제거 (정규화 기준)"""
        self.logger.info("🔧 중복 URL 제거 중...")

        try:
            # 모든 레코드 읽기
            records = self.get_all_records()

            # 정규화된 URL 기준으로 중복 제거
            seen_urls = set()
            unique_records = []

            for record in records:
                normalized = normalize_url(record.product_url)
                if normalized not in seen_urls:
                    seen_urls.add(normalized)
                    unique_records.append(record)

            # 파일 다시 쓰기
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()

                for record in unique_records:
                    writer.writerow(record.to_dict())

            removed_count = len(records) - len(unique_records)
            self.logger.info(f"✅ 중복 제거 완료: {removed_count}개 제거, {len(unique_records)}개 남음")

        except Exception as e:
            self.logger.error(f"중복 제거 실패: {e}")
