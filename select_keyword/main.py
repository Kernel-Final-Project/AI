from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Sequence

from .selector import KeywordSelector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEYWORD_FILE = PROJECT_ROOT / "keywords.csv"
DEFAULT_EXCLUDE_FILE = PROJECT_ROOT / "excep.csv"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """CLI 인자를 파싱해 실행 시 필요한 설정 값을 준비한다."""
    parser = argparse.ArgumentParser(description="GPT 기반 키워드 선택기")
    parser.add_argument(
        "--keywords-csv",
        type=Path,
        default=DEFAULT_KEYWORD_FILE,
        help=f"키워드 목록 CSV 경로 (기본값: {DEFAULT_KEYWORD_FILE})",
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI 모델명")
    parser.add_argument("--temperature", type=float, default=0.3, help="샘플링 온도")
    parser.add_argument("--max-keywords", type=int, default=50, help="최대 키워드 수")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="출력 형식 (json 또는 키워드만 출력)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과를 저장할 경로 (생략 시 stdout에만 출력)",
    )
    parser.add_argument(
        "--exclude-csv",
        type=Path,
        default=DEFAULT_EXCLUDE_FILE,
        help=f"제외할 키워드 목록 CSV 경로 (기본값: {DEFAULT_EXCLUDE_FILE}, 없으면 무시)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="로깅 레벨 (DEBUG/INFO/WARNING/ERROR)",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    """간단한 로그 포맷을 지정하고 콘솔에 바로 출력되도록 설정한다."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )


def serialize_result(result, output_format: str) -> str:
    """결과 객체를 사용자 지정 형식(text/json)으로 문자열화한다."""
    if output_format == "text":
        return result.keyword
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    """명령줄 인터페이스 진입점."""
    args = parse_args(argv)
    configure_logging(args.log_level)

    try:
        selector = KeywordSelector(model=args.model, temperature=args.temperature)
        result = selector.select_from_file(
            args.keywords_csv,
            limit=args.max_keywords,
            exclude_path=args.exclude_csv,
        )
    except Exception as exc:  # pragma: no cover - CLI convenience
        logging.error("키워드 선택 실패: %s", exc)
        return 1

    rendered = serialize_result(result, args.format)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        content = rendered if args.format == "json" else f"{rendered}\n"
        args.output.write_text(content, encoding="utf-8")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
