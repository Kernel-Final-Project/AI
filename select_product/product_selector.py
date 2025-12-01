from __future__ import annotations

import csv
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from openai import OpenAI

from common.utils import load_env_from_default_locations

logger = logging.getLogger(__name__)


def _normalize_key(value: str | None) -> str:
    """소문자+공백 제거 버전을 만들어 비교에 쓰기 쉽게 한다."""
    if not value:
        return ""
    normalized = re.sub(r"\s+", "", value)
    return normalized.lower()


def _aliases(*keys: str) -> tuple[str, ...]:
    """여러 필드명을 한 번에 normalize해 비교 alias를 구축한다."""
    return tuple(_normalize_key(key) for key in keys)


NAME_KEYS = _aliases(
    "product_name",
    "product name",
    "name",
    "title",
    "상품명",
    "제품명",
    "아이템명",
    "상품명(국문)",
)
DESC_KEYS = _aliases(
    "description",
    "desc",
    "요약",
    "설명",
    "특징",
    "한줄설명",
    "product_description",
)
PRICE_KEYS = _aliases("price", "판매가", "가격", "최종가", "할인가")
URL_KEYS = _aliases("url", "link", "상품링크", "product_url", "detail_url", "구매링크")


def _is_header_token(token: str) -> bool:
    """CSV 첫 줄이 헤더인지 대강 판별해 실데이터와 구분한다."""
    normalized = _normalize_key(token)
    return normalized in {
        *_aliases("keyword", "product", "product_name", "상품명"),
    }


def _extract_by_alias(row: Dict[str, str], aliases: Sequence[str]) -> Optional[str]:
    """여러 가능한 헤더명 중 일치하는 항목이 있으면 해당 값을 돌려준다."""
    for key, value in row.items():
        if not value:
            continue
        if _normalize_key(key) in aliases:
            return value
    return None


@dataclass
class Product:
    """CSV 한 줄을 구조화해 GPT 프롬프트에 활용하기 위한 컨테이너."""

    name: str
    description: Optional[str]
    price: Optional[str]
    url: Optional[str]
    extra: Dict[str, str]

    def normalized_name(self) -> str:
        return _normalize_key(self.name)

    def prompt_block(self, index: int) -> str:
        lines = [f"{index}. {self.name}"]
        if self.description:
            lines.append(f"   설명: {self.description}")
        if self.price:
            lines.append(f"   가격: {self.price}")
        if self.url:
            lines.append(f"   링크: {self.url}")

        extra_pairs = []
        for key, value in self.extra.items():
            if not value:
                continue
            extra_pairs.append(f"{key}: {value}")
            if len(extra_pairs) >= 3:
                break

        if extra_pairs:
            lines.append(f"   기타: {', '.join(extra_pairs)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "url": self.url,
            "extra": self.extra,
        }


@dataclass
class ProductSelectionResult:
    """GPT가 고른 상품과 원본 레코드를 묶어서 전달하는 컨테이너."""

    keyword: str
    product_name: str
    reason: str
    product: Product
    raw_response: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["product"] = self.product.to_dict()
        return data


def _standardize_row(raw_row: Dict[str, str | None]) -> Dict[str, str]:
    cleaned: Dict[str, str] = {}
    for key, value in raw_row.items():
        if key is None:
            continue
        cleaned_key = key.strip()
        cleaned_value = (value or "").strip()
        cleaned[cleaned_key] = cleaned_value
    return cleaned


def _load_exclusions(csv_path: Optional[Path]) -> set[str]:
    """과거에 이미 선택된 상품명을 normalized 형태로 집합에 적재한다."""
    if not csv_path:
        return set()
    if not csv_path.is_file():
        return set()

    excluded: set[str] = set()
    with csv_path.open("r", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        for row in reader:
            cells = [cell.strip() for cell in row if cell and cell.strip()]
            if not cells:
                continue
            token = cells[0]
            if not excluded and _is_header_token(token):
                continue
            excluded.add(_normalize_key(token))
    return excluded


def load_products(
    csv_path: Path,
    limit: Optional[int] = None,
    exclude_path: Optional[Path] = None,
) -> List[Product]:
    """상품 CSV를 읽어 Product 리스트로 정규화한다."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"상품 CSV를 찾을 수 없습니다: {csv_path}")

    excluded = _load_exclusions(exclude_path)
    products: List[Product] = []

    with csv_path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for idx, raw_row in enumerate(reader):
            row = _standardize_row(raw_row)
            if not any(row.values()):
                continue

            name = _extract_by_alias(row, NAME_KEYS)
            if not name:
                name = next((value for value in row.values() if value), None)
            if not name:
                name = f"상품 {idx + 1}"

            normalized_name = _normalize_key(name)
            # 이미 과거에 선택된 상품은 프롬프트에서 제외한다.
            if normalized_name in excluded:
                continue

            description = _extract_by_alias(row, DESC_KEYS)
            price = _extract_by_alias(row, PRICE_KEYS)
            url = _extract_by_alias(row, URL_KEYS)

            reserved = set(NAME_KEYS + DESC_KEYS + PRICE_KEYS + URL_KEYS)
            extra = {
                key: value
                for key, value in row.items()
                if value and _normalize_key(key) not in reserved
            }

            product = Product(
                name=name,
                description=description,
                price=price,
                url=url,
                extra=extra,
            )
            products.append(product)

            if limit and len(products) >= limit:
                break

    if not products:
        raise ValueError(f"상품 CSV에서 선택 가능한 항목을 찾지 못했습니다: {csv_path}")
    return products


DEFAULT_SYSTEM_PROMPT = (
    "You are a senior Korean e-commerce MD. "
    "Given a list of product candidates and a target keyword, "
    "choose exactly one product that maximizes purchase conversion potential. "
    "Always answer in Korean."
)


class ProductSelector:
    """상품 목록과 타깃 키워드를 GPT에게 전달해 단일 추천을 받는 헬퍼."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.4,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._ensure_env(api_key)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt

    @staticmethod
    def _ensure_env(api_key: Optional[str]) -> None:
        if api_key:
            return
        if os.getenv("OPENAI_API_KEY"):
            return
        load_env_from_default_locations(Path(__file__).resolve())

    @staticmethod
    def build_user_prompt(keyword: str, products: Sequence[Product]) -> str:
        instructions = (
            f"선정된 블로그 키워드: {keyword}\n\n"
            "위 키워드와 가장 궁합이 좋고 구매 전환 가능성이 높은 상품 1개를 골라주세요.\n"
            "- 키워드와의 직접적인 연관성, 계절성, 가격 경쟁력, 차별화 포인트를 고려하세요.\n"
            "- 중복되거나 이미 선정된 상품은 피하고, 이유는 한 문장으로 요약합니다."
        )
        # 프롬프트를 만들 때 각 상품을 번호+간단한 디테일로 나열한다.
        product_lines = [product.prompt_block(idx + 1) for idx, product in enumerate(products)]
        format_hint = (
            '\n\n반드시 다음 JSON 형식으로만 답변하세요:\n'
            '{\n'
            '  "product_name": "선택한 상품명",\n'
            '  "reason": "선택 이유",\n'
            '  "notes": "추가로 강조하고 싶은 포인트 (선택)"\n'
            "}"
        )
        return f"{instructions}\n\n상품 목록:\n" + "\n".join(product_lines) + format_hint

    def select(
        self,
        keyword: str,
        products: Sequence[Product],
        max_retries: int = 2,
    ) -> ProductSelectionResult:
        if not keyword.strip():
            raise ValueError("선택된 키워드가 비어 있습니다.")
        if not products:
            raise ValueError("선택할 상품 목록이 없습니다.")

        user_prompt = self.build_user_prompt(keyword.strip(), products)
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                raw_response = self._call_gpt(user_prompt)
                parsed = self._parse_response(raw_response)
                product = self._match_product(parsed.get("product_name"), products)
                reason = parsed.get("reason") or "GPT 응답을 확인하세요."
                return ProductSelectionResult(
                    keyword=keyword.strip(),
                    product_name=product.name,
                    reason=reason,
                    product=product,
                    raw_response=raw_response,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                last_error = exc
                logger.warning("GPT 상품 선택 실패 (%s/%s): %s", attempt, max_retries, exc)

        raise RuntimeError("GPT를 사용한 상품 선택에 실패했습니다.") from last_error

    def _call_gpt(self, user_prompt: str) -> str:
        # Chat Completions API를 호출해 JSON 문자열을 받아온다.
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _parse_response(self, raw_response: str) -> dict:
        data = self._extract_json(raw_response)
        product_name = str(
            data.get("product_name") or data.get("name") or data.get("keyword") or ""
        ).strip()
        reason = str(data.get("reason") or data.get("why") or "").strip()
        notes = str(data.get("notes") or "").strip()
        payload = {"product_name": product_name, "reason": reason}
        if notes:
            payload["notes"] = notes
        return payload

    def _match_product(self, product_name: str, products: Sequence[Product]) -> Product:
        normalized_map = {product.normalized_name(): product for product in products}
        normalized_name = _normalize_key(product_name)
        matched = normalized_map.get(normalized_name)
        if not matched:
            if product_name:
                logger.warning("선택된 상품이 목록에 없습니다: %s", product_name)
            matched = products[0]
        return matched

    @staticmethod
    def _extract_json(raw_response: str) -> dict:
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {"product_name": raw_response.strip(), "reason": ""}
