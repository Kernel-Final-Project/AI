
"""
상품 정보 추출 테스트 - Selenium 버전 (블로그 생성 제외)
안정적이고 봇 탐지 우회 기능 강화

사용방법:
python test_product_extraction_selenium.py \
    --base-url "https://www.coupang.com" \
    --keyword "맨투맨" \
    --output "outputs/product_test_selenium.json"
"""

import argparse
import logging
from pathlib import Path

from common.utils import configure_logging, write_json, load_env_from_default_locations
from url_refiner import URLRefiner
from product_scraper.selenium_product_selector import SeleniumProductSelector
from product_scraper.selenium_product_extractor import SeleniumProductExtractor
from product_scraper.product_history import ProductHistory

logger = logging.getLogger(__name__)


def main(args):
    """메인 함수"""

    # 환경 변수 로드
    load_env_from_default_locations()

    # 로깅 설정
    log_level_str = "DEBUG" if args.verbose else "INFO"
    log_file = configure_logging(Path("logs"), log_level_str)
    logger.info(f"로그 파일: {log_file}")

    selenium_selector = None

    try:
        # Step 1: URL 정제
        logger.info("\n📍 STEP 1: URL 정제")
        url_refiner = URLRefiner()
        refine_result = url_refiner.refine(args.base_url, args.keyword)
        logger.info(f"✅ 정제된 URL: {refine_result.refined_url}")

        # Step 2: 히스토리 로드
        logger.info("\n📍 STEP 2: 기존 상품 히스토리 확인")
        product_history = ProductHistory(csv_path=args.product_list)
        exclude_urls = product_history.get_all_urls()
        logger.info(f"📚 제외할 상품: {len(exclude_urls)}개")

        # Step 3: 상품 URL 랜덤 선택 (Selenium)
        logger.info("\n📍 STEP 3: 상품 URL 랜덤 선택 (Selenium 스텔스 모드)")
        selenium_selector = SeleniumProductSelector(headless=args.headless)
        selenium_selector.initialize(start_url=args.base_url)

        selected_product = selenium_selector.select_product(
            search_url=refine_result.refined_url,
            keyword=args.keyword,
            exclude_urls=exclude_urls
        )
        logger.info(f"✅ 선택된 상품 URL: {selected_product.product_url}")

        # Step 4: 상품 상세 정보 추출
        logger.info("\n📍 STEP 4: 상품 상세 정보 추출 (Selenium)")
        product_extractor = SeleniumProductExtractor(headless=args.headless)
        product_detail = product_extractor.extract_product_info(
            product_url=selected_product.product_url
        ).to_dict()

        # Step 5: 결과 검증
        logger.info("\n📍 STEP 5: 결과 검증")
        if not product_detail or not product_detail.get("name"):
            raise ValueError("상품 정보 추출 실패: name이 없습니다")

        logger.info(f"✅ 상품명: {product_detail.get('name')}")
        logger.info(f"✅ 브랜드: {product_detail.get('brand', 'N/A')}")
        logger.info(f"✅ 가격: {product_detail.get('price', 'N/A')}")

        # Step 6: 결과 저장
        logger.info("\n📍 STEP 6: 결과 저장")

        # 히스토리에 추가 (중복 방지 로직 내부 포함)
        product_history.add_product(
            product_url=selected_product.product_url,
            keyword=args.keyword,
            product_name=product_detail.get("name")
        )

        output_data = {
            "selected_product": {
                "url": selected_product.product_url,
                "reason": selected_product.reason,
            },
            "product_detail": product_detail
        }

        write_json(Path(args.output), output_data)
        logger.info(f"✅ 결과 저장 완료: {args.output}")

        logger.info("\n✅ 테스트 성공!")
        return 0

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        return 1

    finally:
        # 리소스 정리
        if selenium_selector:
            try:
                selenium_selector.close()
            except Exception as e:
                logger.error(f"Selenium 종료 중 오류: {e}")


def parse_args():
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="상품 정보 추출 테스트 (Selenium 버전)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python test_product_extraction_selenium.py \\
      --base-url "https://www.coupang.com" \\
      --keyword "맨투맨" \\
      --output "outputs/product_test_selenium.json"
        """
    )

    parser.add_argument(
        "--base-url",
        type=str,
        required=True,
        help="쇼핑몰 기본 URL (예: https://www.coupang.com)"
    )

    parser.add_argument(
        "--keyword",
        type=str,
        required=True,
        help="검색 키워드 (예: 니트, 맨투맨)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="outputs/product_test_selenium.json",
        help="결과 저장 경로 (기본: outputs/product_test_selenium.json)"
    )

    parser.add_argument(
        "--product-list",
        type=str,
        default="product_list.csv",
        help="상품 히스토리 CSV 파일 경로 (기본: product_list.csv)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Headless 모드 (기본: False, 브라우저 창 보임)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력 (DEBUG 레벨)"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit(main(args))
