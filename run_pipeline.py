#!/usr/bin/env python3
"""키워드 크롤링→GPT 선택→콘텐츠 생성을 하나의 러너로 묶는 스크립트."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence

from common.utils import configure_logging, write_json
from generate_content.content_generator import ContentGenerator, GeneratedContent, ProductContext
from keywordCrawler.keywordCrawler.cli import crawl_keywords
from select_keyword.selector import KeywordSelector, SelectionResult, load_keywords
from select_product.product_selector import ProductSelector, ProductSelectionResult, load_products


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Itemscout 키워드부터 블로그 콘텐츠까지 한 번에 생성합니다.",
    )
    parser.add_argument("--c1", required=True, help="1차 카테고리")
    parser.add_argument("--c2", help="2차 카테고리")
    parser.add_argument("--c3", help="3차 카테고리")
    parser.add_argument("--headless", action="store_true", help="브라우저 headless 모드")
    parser.add_argument("--wait-timeout", type=int, default=15, help="Selenium 명시적 대기 타임아웃")
    parser.add_argument("--delay", type=float, default=0.3, help="카테고리 선택 사이 지연 (초)")
    parser.add_argument("--keyword-limit", type=int, default=50, help="GPT에 넘길 최대 키워드 수")
    parser.add_argument("--max-products", type=int, default=30, help="GPT 후보 상품 수")
    parser.add_argument(
        "--product-list",
        type=Path,
        default=Path("product_list.csv"),
        help="상품 후보 CSV 경로 (기본: product_list.csv)",
    )
    parser.add_argument(
        "--past-products",
        type=Path,
        default=Path("past_selected_product_list.csv"),
        help="제외할 과거 상품 CSV 경로 (기본: past_selected_product_list.csv)",
    )
    parser.add_argument(
        "--keyword-exclude",
        type=Path,
        default=Path("excep.csv"),
        help="제외할 키워드 CSV 경로 (기본: excep.csv)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("outputs/pipeline_result.json"),
        help="최종 산출물 JSON 경로 (기본: outputs/pipeline_result.json)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="루트 로거 레벨 (DEBUG/INFO/…)",
    )
    return parser.parse_args(argv)


def run_keyword_step(args: argparse.Namespace, output_csv: Path) -> None:
    logging.info("1/4 키워드 크롤링 시작 (출력: %s)", output_csv)
    crawl_keywords(
        args.c1,
        args.c2,
        args.c3,
        output_path=output_csv,
        headless=args.headless,
        wait_timeout=args.wait_timeout,
        delay=args.delay,
    )
    logging.info("1/4 키워드 크롤링 완료")


def select_keyword_step(
    keywords_csv: Path,
    exclude_csv: Path | None,
    limit: int,
) -> tuple[list[str], SelectionResult]:
    logging.info("2/4 GPT 키워드 선택 시작")
    exclude_path = exclude_csv if exclude_csv and exclude_csv.is_file() else None
    keywords = load_keywords(keywords_csv, limit=limit, exclude_path=exclude_path)
    selector = KeywordSelector()
    selection = selector.select(keywords)
    logging.info("2/4 GPT 키워드 선택 완료 → %s", selection.keyword)
    return keywords, selection


def select_product_step(
    keyword: str,
    product_list: Path,
    past_products: Path | None,
    limit: int,
) -> ProductSelectionResult:
    logging.info("3/4 GPT 상품 선택 시작")
    exclude_path = past_products if past_products and past_products.is_file() else None
    products = load_products(product_list, limit=limit, exclude_path=exclude_path)
    selector = ProductSelector()
    result = selector.select(keyword=keyword, products=products)
    logging.info("3/4 GPT 상품 선택 완료 → %s", result.product_name)
    return result


def generate_content_step(
    keyword: str,
    product_result: ProductSelectionResult,
) -> GeneratedContent:
    logging.info("4/4 콘텐츠 생성 시작")
    context = ProductContext(
        keyword=keyword,
        product_name=product_result.product_name,
        description=product_result.product.description,
        price=product_result.product.price,
        url=product_result.product.url,
        extra=product_result.product.extra,
    )
    generator = ContentGenerator()
    content = generator.generate(context)
    logging.info("4/4 콘텐츠 생성 완료 → 제목: %s", content.title)
    return content


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parent

    log_file = configure_logging(project_root / "logs", args.log_level)
    logging.info("로그 파일: %s", log_file)

    product_list = (project_root / args.product_list).resolve()
    if not product_list.is_file():
        raise FileNotFoundError(f"상품 목록 CSV를 찾을 수 없습니다: {product_list}")
    logging.info("상품 후보 CSV: %s", product_list)

    past_products = (project_root / args.past_products).resolve()
    if past_products.exists():
        logging.info("과거 상품 제외 CSV 사용: %s", past_products)
    else:
        past_products = None

    keyword_exclude = (project_root / args.keyword_exclude).resolve()
    if keyword_exclude.exists():
        logging.info("키워드 제외 CSV 사용: %s", keyword_exclude)
    else:
        keyword_exclude = None

    output_path = (project_root / args.output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="pipeline-", dir=str(project_root)))
    keywords_csv = temp_dir / "keywords.csv"

    try:
        run_keyword_step(args, keywords_csv)
        keywords, keyword_result = select_keyword_step(
            keywords_csv, keyword_exclude, args.keyword_limit
        )
        product_result = select_product_step(
            keyword_result.keyword, product_list, past_products, args.max_products
        )
        content_result = generate_content_step(keyword_result.keyword, product_result)

        pipeline_result = {
            "metadata": {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "categories": {
                    "c1": args.c1,
                    "c2": args.c2,
                    "c3": args.c3,
                },
                "log_file": str(log_file.relative_to(project_root)),
            },
            "keywords": {
                "candidates": keywords,
                "selected": keyword_result.to_dict(),
            },
            "product": product_result.to_dict(),
            "content": content_result.to_dict(),
        }

        write_json(output_path, pipeline_result)
        logging.info("최종 산출물 저장: %s", output_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logging.debug("임시 디렉터리 정리: %s", temp_dir)

    logging.info("파이프라인 완료!")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
