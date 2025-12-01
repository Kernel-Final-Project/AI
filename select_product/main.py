"""선택된 키워드 기반으로 GPT에게 최적 상품 1개를 고르게 하는 CLI."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Sequence

from .product_selector import ProductSelector, load_products

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS_FILE = PROJECT_ROOT / "product_list.csv"
DEFAULT_EXCLUDE_FILE = PROJECT_ROOT / "past_selected_product_list.csv"
DEFAULT_KEYWORD_FILE = PROJECT_ROOT / "selected_keyword.csv"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GPT 기반 상품 선택기")
    parser.add_argument(
        "--products-csv",
        type=Path,
        default=DEFAULT_PRODUCTS_FILE,
        help=f"상품 목록 CSV 경로 (기본값: {DEFAULT_PRODUCTS_FILE})",
    )
    parser.add_argument(
        "--exclude-csv",
        type=Path,
        default=DEFAULT_EXCLUDE_FILE,
        help="과거 선택 상품 CSV (기본: past_selected_product_list.csv, 없으면 무시)",
    )
    parser.add_argument(
        "--selected-keyword-file",
        type=Path,
        default=DEFAULT_KEYWORD_FILE,
        help="선택된 키워드를 포함한 파일(JSON/CSV). 기본값: selected_keyword.csv",
    )
    parser.add_argument(
        "--keyword",
        help="파일 대신 직접 키워드를 전달하고 싶을 때 사용",
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI 모델명")
    parser.add_argument("--temperature", type=float, default=0.4, help="샘플링 온도")
    parser.add_argument("--max-products", type=int, default=30, help="최대 후보 상품 수")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="출력 형식 (json 또는 상품명만 출력)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과 저장 경로 (생략 시 stdout만 사용)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="로깅 레벨 (DEBUG/INFO/WARNING/ERROR)",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )


def _normalize_token(value: str) -> str:
    return value.replace(" ", "").lower()


def load_selected_keyword(path: Path) -> str:
    """선택된 키워드를 CSV 또는 JSON 형식에서 읽어온다."""
    if not path.is_file():
        raise FileNotFoundError(f"선택된 키워드 파일을 찾을 수 없습니다: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        keyword = data.get("keyword") or data.get("product_keyword")
        if not keyword:
            raise ValueError("JSON에서 'keyword' 필드를 찾을 수 없습니다.")
        return str(keyword).strip()

    with path.open("r", encoding="utf-8") as fp:
        reader = csv.reader(fp)
        for row_index, row in enumerate(reader):
            cells = [cell.strip() for cell in row if cell and cell.strip()]
            if not cells:
                continue
            token = cells[0]
            if row_index == 0 and _normalize_token(token) in {"keyword", "선정키워드", "selectedkeyword"}:
                continue
            return token

    raise ValueError(f"키워드 정보를 읽을 수 없습니다: {path}")


def serialize_result(result, output_format: str) -> str:
    if output_format == "text":
        return result.product_name
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    try:
        # 1) 키워드 로드 → 2) 상품 후보 로드/필터 → 3) GPT에게 최적 상품 요청.
        keyword = args.keyword.strip() if args.keyword else load_selected_keyword(args.selected_keyword_file)
        products = load_products(
            args.products_csv,
            limit=args.max_products,
            exclude_path=args.exclude_csv,
        )
        selector = ProductSelector(model=args.model, temperature=args.temperature)
        result = selector.select(keyword=keyword, products=products)
    except Exception as exc:  # pragma: no cover
        logging.error("상품 선택 실패: %s", exc)
        return 1

    # JSON 혹은 단순 텍스트 형식으로 결과를 렌더링하고 사용자에게 반환한다.
    rendered = serialize_result(result, args.format)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        content = rendered if args.format == "json" else f"{rendered}\n"
        args.output.write_text(content, encoding="utf-8")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
