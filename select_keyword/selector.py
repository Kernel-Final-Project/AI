from __future__ import annotations

import csv
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Sequence

from openai import OpenAI

from common.utils import load_env_from_default_locations

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a senior Korean e-commerce strategist. "
    "Select exactly one keyword for the next blog post, focusing on purchase intent, "
    "trend momentum, and differentiation. Always respond in Korean."
)


@dataclass
class SelectionResult:
    """GPT 선택 결과를 구조화해 다루기 위한 단순 데이터 컨테이너."""

    keyword: str
    reason: str
    raw_response: str

    def to_dict(self) -> dict:
        return asdict(self)


def _load_exclusions(exclude_path: Optional[Path]) -> set[str]:
    """제외 키워드 CSV에서 소문자 normalized 항목을 집합으로 읽어온다."""
    if not exclude_path:
        return set()
    if not exclude_path.is_file():
        return set()

    excluded: set[str] = set()
    with exclude_path.open("r", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        for idx, row in enumerate(reader):
            if not row:
                continue
            token = row[0].strip()
            if not token:
                continue
            header_candidate = token.replace(" ", "").lower()
            if idx == 0 and header_candidate in {"keyword", "키워드", "exclude", "제외"}:
                continue
            excluded.add(token.lower())
    return excluded


def load_keywords(
    csv_path: Path,
    limit: Optional[int] = 50,
    exclude_path: Optional[Path] = None,
) -> List[str]:
    """CSV에서 중복 제거 및 제외 목록 필터링을 적용한 키워드 목록을 읽어온다."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"키워드 CSV를 찾을 수 없습니다: {csv_path}")

    excluded = _load_exclusions(exclude_path)
    keywords: List[str] = []
    seen: set[str] = set()

    with csv_path.open("r", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        for idx, row in enumerate(reader):
            if not row:
                continue
            first_col = row[0].strip()
            if not first_col:
                continue
            if idx == 0 and first_col.replace(" ", "").lower() in {"keyword", "키워드"}:
                continue
            normalized = first_col.lower()
            if normalized in seen:
                continue
            if normalized in excluded:
                continue
            seen.add(normalized)
            keywords.append(first_col)
            if limit and len(keywords) >= limit:
                break

    if not keywords:
        raise ValueError(f"CSV에서 유효한 키워드를 찾지 못했습니다: {csv_path}")
    return keywords


class KeywordSelector:
    """키워드 목록을 GPT에 전달해 최적의 하나를 선택하도록 돕는 헬퍼."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
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
    def build_user_prompt(keywords: Sequence[str]) -> str:
        """GPT가 이해하기 쉬운 지침과 JSON 응답 포맷 힌트를 조합한다."""
        bullet_list = "\n".join(f"{idx + 1}. {keyword}" for idx, keyword in enumerate(keywords))
        instructions = (
            "다음 키워드 목록에서 블로그 주제로 가장 가치 있는 1개만 골라주세요.\n"
            "- 구매 의도가 뚜렷하고 구체적인 표현을 우선합니다.\n"
            "- 계절/시즌 혹은 최근 이슈와 맞으면 가산점을 줍니다.\n"
            "- 지나치게 일반적인 표현은 피합니다.\n"
            "선택 이유는 한 문장으로 요약하세요."
        )
        format_hint = (
            '\n\n반드시 다음 JSON 형식으로만 답해주세요:\n'
            '{\n  "keyword": "선택한 키워드",\n  "reason": "선정 이유"\n}'
        )
        return f"{instructions}\n\n키워드 목록:\n{bullet_list}{format_hint}"

    def select(self, keywords: Sequence[str], max_retries: int = 2) -> SelectionResult:
        """키워드 배열을 받아 GPT 호출→응답 파싱까지 한 번에 처리한다."""
        normalized_keywords = [kw.strip() for kw in keywords if kw.strip()]
        if not normalized_keywords:
            raise ValueError("선택할 키워드가 없습니다.")

        user_prompt = self.build_user_prompt(normalized_keywords)
        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                raw_response = self._call_gpt(user_prompt)
                parsed = self._parse_response(raw_response, normalized_keywords)
                return SelectionResult(keyword=parsed["keyword"], reason=parsed["reason"], raw_response=raw_response)
            except Exception as exc:  # pragma: no cover - defensive logging
                last_error = exc
                logger.warning("GPT 호출 실패 (%s/%s): %s", attempt, max_retries, exc, exc_info=False)
        raise RuntimeError("GPT 호출에 실패했습니다.") from last_error

    def select_from_file(
        self,
        csv_path: Path,
        limit: Optional[int] = 50,
        exclude_path: Optional[Path] = None,
    ) -> SelectionResult:
        """CSV 입력을 읽어 select()로 위임한다."""
        keywords = load_keywords(csv_path, limit, exclude_path=exclude_path)
        return self.select(keywords)

    def _call_gpt(self, user_prompt: str) -> str:
        """OpenAI Chat Completions API를 호출해 원시 응답 메시지를 반환한다."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _parse_response(self, raw_response: str, candidates: Sequence[str]) -> dict:
        """JSON 응답을 파싱하고 누락 값은 안전한 기본값으로 보완한다."""
        data = self._extract_json(raw_response)
        keyword = str(data.get("keyword", "")).strip()
        reason = str(data.get("reason", "")).strip()

        normalized_map = {candidate.lower(): candidate for candidate in candidates}
        normalized_keyword = keyword.lower()
        selected_keyword = normalized_map.get(normalized_keyword)

        if not selected_keyword:
            if keyword:
                logger.warning("선택된 키워드가 목록에 없습니다: %s", keyword)
            selected_keyword = candidates[0]

        if not reason:
            reason = "GPT 응답을 확인하세요."

        return {"keyword": selected_keyword, "reason": reason}

    @staticmethod
    def _extract_json(raw_response: str) -> dict:
        """응답 본문에서 JSON을 추출하되 실패하면 텍스트를 그대로 되돌린다."""
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

        return {"keyword": raw_response.strip(), "reason": ""}
