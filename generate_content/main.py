"""select_product 결과를 받아 블로그 콘텐츠를 만들어 주는 CLI."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Sequence

from .content_generator import ContentGenerator, ProductContext

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCT_SELECTION_FILE = PROJECT_ROOT / "selected_product.json"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="상품 기반 블로그 콘텐츠 생성기")
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=DEFAULT_PRODUCT_SELECTION_FILE,
        help="선택된 상품 정보를 담은 JSON 경로 (기본: selected_product.json)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI 모델명",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="샘플링 온도",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="출력 형식 (json 또는 Markdown 본문만 출력)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과 저장 경로 (생략 시 stdout만 사용)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="로깅 레벨",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )


def load_selection_file(path: Path) -> ProductContext:
    """select_product JSON을 읽어 ProductContext로 변환한다."""
    if not path.is_file():
        raise FileNotFoundError(f"선택된 상품 정보를 찾을 수 없습니다: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProductContext.from_json(data)


def serialize_result(result, output_format: str) -> str:
    if output_format == "text":
        return f"# {result.title}\n\n{result.content}"
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    try:
        # 1) 상품 컨텍스트 로딩 → 2) GPT 호출 → 3) 결과 렌더링.
        context = load_selection_file(args.selection_file)
        generator = ContentGenerator(model=args.model, temperature=args.temperature)
        result = generator.generate(context)
    except Exception as exc:  # pragma: no cover
        logging.error("콘텐츠 생성 실패: %s", exc)
        return 1

    # JSON 혹은 텍스트 형태로 결과를 출력/저장한다.
    rendered = serialize_result(result, args.format)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        content = rendered if args.format == "json" else f"{rendered}\n"
        args.output.write_text(content, encoding="utf-8")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
