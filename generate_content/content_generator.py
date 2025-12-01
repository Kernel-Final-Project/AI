"""상품 정보를 받아 블로그용 제목/본문을 생성하는 OpenAI 도우미."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional

from openai import OpenAI

from common.utils import load_env_from_default_locations

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a top-tier Korean e-commerce copywriter. "
    "Craft compelling blog posts that highlight a product's strengths, "
    "focusing on storytelling, user benefits, and conversion. "
    "Always write in fluent Korean."
)


@dataclass
class ProductContext:
    """콘텐츠 작성에 필요한 키워드·상품 정보를 보관한다."""

    keyword: str
    product_name: str
    description: Optional[str]
    price: Optional[str]
    url: Optional[str]
    extra: Dict[str, str]

    @classmethod
    def from_json(cls, data: Dict) -> "ProductContext":
        """select_product 출력(JSON)에서 필요한 필드를 뽑아온다."""
        keyword = str(data.get("keyword") or data.get("selected_keyword") or "").strip()
        product_info = data.get("product") or {}
        name = str(
            product_info.get("name") or data.get("product_name") or data.get("name") or ""
        ).strip()
        if not keyword or not name:
            raise ValueError("콘텐츠 생성에 필요한 keyword 또는 product_name이 없습니다.")

        description = (
            product_info.get("description")
            or data.get("description")
            or data.get("summary")
        )
        price = product_info.get("price") or data.get("price")
        url = product_info.get("url") or data.get("url")
        extra = product_info.get("extra") or {}
        if not isinstance(extra, dict):
            extra = {}

        return cls(
            keyword=keyword,
            product_name=name,
            description=description,
            price=price,
            url=url,
            extra=extra,
        )

    def to_prompt(self) -> str:
        """GPT에게 건넬 한국어 프롬프트 문자열을 조합한다."""
        parts = [
            f"선정된 블로그 키워드: {self.keyword}",
            f"주요 상품명: {self.product_name}",
        ]

        if self.description:
            parts.append(f"상품 설명: {self.description}")
        if self.price:
            parts.append(f"가격 정보: {self.price}")
        if self.url:
            parts.append(f"구매 링크: {self.url}")

        if self.extra:
            extra_lines = [f"{key}: {value}" for key, value in self.extra.items()]
            parts.append("추가 정보:\n" + "\n".join(extra_lines))

        instructions = (
            "위 정보를 참고해 블로그 홍보용 콘텐츠를 작성하세요.\n"
            "- 제목은 클릭을 유도하는 매력적인 문구로 1개만 작성합니다.\n"
            "- 본문은 최소 5개 단락으로 구성하고, 상품 장점/사용 시나리오/구매 유도 요소를 포함하세요.\n"
            "- 마크다운 문법을 사용해 소제목, 강조, 리스트 등을 적절히 섞어주세요.\n"
            "- 지나친 과장은 피하고, 실제 구매자가 궁금해할 정보에 집중하세요."
        )
        format_hint = (
            '\n\n반드시 다음 JSON 형식으로 답해주세요:\n'
            '{\n'
            '  "title": "블로그 글 제목",\n'
            '  "content": "마크다운 본문"\n'
            "}"
        )

        return "\n".join(parts + ["", instructions, format_hint])


@dataclass
class GeneratedContent:
    """GPT가 반환한 제목, 본문, 원본 응답을 담는 DTO."""

    title: str
    content: str
    raw_response: str

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


class ContentGenerator:
    """OpenAI Chat Completions API로 블로그 콘텐츠를 만든다."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.6,
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

    def generate(self, context: ProductContext, max_retries: int = 2) -> GeneratedContent:
        """필요시 재시도하면서 제목/본문을 확보한다."""
        prompt = context.to_prompt()
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                raw_response = self._call_gpt(prompt)
                data = self._parse_response(raw_response)
                return GeneratedContent(
                    title=data["title"],
                    content=data["content"],
                    raw_response=raw_response,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                last_error = exc
                logger.warning("콘텐츠 생성 실패 (%s/%s): %s", attempt, max_retries, exc)

        raise RuntimeError("GPT를 사용한 콘텐츠 생성에 실패했습니다.") from last_error

    def _call_gpt(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _parse_response(self, raw_response: str) -> Dict[str, str]:
        """JSON 문자열을 파싱하고 필수 필드가 있는지 확인한다."""
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            data = self._extract_json(raw_response)

        title = str(data.get("title") or data.get("subject") or "").strip()
        content = str(data.get("content") or data.get("body") or "").strip()

        if not title or not content:
            raise ValueError("GPT 응답에서 제목 또는 본문을 찾지 못했습니다.")

        return {"title": title, "content": content}

    @staticmethod
    def _extract_json(raw_response: str) -> Dict[str, str]:
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw_response[start : end + 1])
            except json.JSONDecodeError:
                pass

        return {"title": raw_response.strip(), "content": ""}
