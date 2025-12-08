"""
  URL 정제 모듈 CLI
  """

import argparse
import logging
from pathlib import Path

from common.utils import configure_logging, write_json
from .refiner import URLRefiner,  UnsupportedShoppingMallError


def main():
    parser = argparse.ArgumentParser(description="URL 정제 도구")
    parser.add_argument("--base-url", required=True, help="쇼핑몰 메인 URL")
    parser.add_argument("--keyword", required=True, help="검색 키워드")
    parser.add_argument("--output", default="outputs/refined_url.json", help="출력 파일")
    parser.add_argument("--verbose", action="store_true", help="상세 로그")
    parser.add_argument("--list", action="store_true", help="지원되는 쇼핑몰 목록 보기")
    parser.add_argument("--no-strict", action="store_true", help="strict 모드 비활성화 (실험적)")

    args = parser.parse_args()


    # 지원 쇼핑몰 목록 출력
    if args.list:
        print("\n📋 지원되는 쇼핑몰 목록:\n")
        malls = URLRefiner.get_supported_malls()
        for i, mall in enumerate(malls, 1):
            print(f"{i}. {mall['name']}")
            print(f"   도메인: {mall['domain']}")
            print(f"   예시 URL: {mall['example_url']}")
            print()
        return

    # base-url과 keyword 필수
    if not args.base_url or not args.keyword:
        parser.error("--base-url과 --keyword는 필수입니다 (또는 --list 사용)")


    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(log_level)

    # URL 정제
    try:
        refiner = URLRefiner(strict_mode=not args.no_strict)
        result = refiner.refine(args.base_url, args.keyword)

        # 결과 저장
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(output_path, result.to_dict())

        print(f"\n✅ 정제 완료!")
        print(f"   원본 URL: {result.original_url}")
        print(f"   키워드: {result.keyword}")
        print(f"   쇼핑몰: {result.shopping_mall}")
        print(f"   정제된 URL: {result.refined_url}")
        print(f"   저장 위치: {output_path}")

    except UnsupportedShoppingMallError as e:
        print(f"\n{str(e)}")
        print("\n💡 지원되는 쇼핑몰 목록을 보려면:")
        print("   python -m url_refiner.main --list")
        exit(1)



if __name__ == "__main__":
    main()