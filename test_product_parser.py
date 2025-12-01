"""
범용 상품 파서 테스트 스크립트
실제 URL을 입력받아 상품 데이터를 추출합니다.
"""

import sys
import json
from scraper.html_extractor import load_html_ssr, load_html_csr
from scraper.product_parser import parse_products
from scraper.ssr_csr_checker import check_ssr_csr
from utils.logger import logger

# 로그 레벨을 WARNING으로 설정 (INFO 메시지 숨김)
import logging

logging.getLogger("ai_blog_project").setLevel(logging.WARNING)


def test_product_parsing_from_url(url: str):
    """
    URL에서 상품 데이터 추출 테스트

    Args:
        url: 테스트할 URL
    """
    print("\n" + "=" * 60)
    print(f"URL에서 상품 데이터 추출 테스트")
    print("=" * 60)
    print(f"\n[입력 URL] {url}")

    try:
        # 1. SSR/CSR 판별
        print("\n[1단계] SSR/CSR 판별 중...")
        check_result = check_ssr_csr(url)
        print(
            f"  ✅ 판별 결과: {check_result.rendering_type} (신뢰도: {check_result.confidence:.2f})"
        )

        # 2. HTML 로드
        print(f"\n[2단계] HTML 로드 중...")
        if check_result.rendering_type == "SSR":
            html, soup = load_html_ssr(url)
            print(f"  ✅ SSR 방식으로 HTML 로드 완료")
        else:
            html, soup = load_html_csr(url)
            print(f"  ✅ CSR 방식으로 HTML 로드 완료")
        print(f"  HTML 크기: {len(html):,} bytes")

        # 3. 상품 파싱
        print(f"\n[3단계] 상품 정보 파싱 중...")
        products = parse_products(soup, url)

        print(f"\n[결과] ✅ 파싱 완료: {len(products)}개 상품 발견")

        if len(products) == 0:
            print("\n  ⚠️  상품을 찾을 수 없습니다.")
            print("  - HTML 구조가 예상과 다를 수 있습니다.")
            print("  - 카테고리/검색 결과 페이지인지 확인해주세요.")
            return

        # 4. 결과 출력 (보기 좋게)
        print("\n" + "=" * 80)
        print("📦 추출된 상품 정보")
        print("=" * 80)

        for i, product in enumerate(products[:50], 1):  # 처음 10개만
            print(f"\n{'─'*80}")
            print(f"상품 {i}/{len(products)}")
            print(f"{'─'*80}")
            print(f"📌 제목: {product.title}")

            if product.price:
                print(f"💰 가격: {product.price}")
            else:
                print(f"💰 가격: ❌ 없음")

            if product.product_code:
                print(f"🔢 상품 코드: {product.product_code}")
            else:
                print(f"🔢 상품 코드: ❌ 없음")

            if product.image_url:
                print(f"🖼️  이미지: {product.image_url}")
            else:
                print(f"🖼️  이미지: ❌ 없음")

            if product.product_url:
                print(f"🔗 링크: {product.product_url}")
            else:
                print(f"🔗 링크: ❌ 없음")

        if len(products) > 10:
            print(f"\n{'─'*80}")
            print(f"  ... 외 {len(products) - 10}개 상품 더 있음")

        # 5. 통계
        print("\n" + "=" * 80)
        print("📊 통계")
        print("=" * 80)
        price_count = sum(1 for p in products if p.price)
        image_count = sum(1 for p in products if p.image_url)
        link_count = sum(1 for p in products if p.product_url)

        code_count = sum(1 for p in products if p.product_code)
        print(f"\n✅ 총 상품 수: {len(products)}개")
        print(f"\n📈 추출 성공률:")
        print(f"  💰 가격 정보: {price_count}개 ({price_count/len(products)*100:.1f}%)")
        print(f"  🔢 상품 코드: {code_count}개 ({code_count/len(products)*100:.1f}%)")
        print(
            f"  🖼️  이미지 URL: {image_count}개 ({image_count/len(products)*100:.1f}%)"
        )
        print(f"  🔗 상품 링크: {link_count}개 ({link_count/len(products)*100:.1f}%)")

        # 6. JSON 형식으로도 저장 (선택)
        print(f"\n💾 JSON 형식으로 저장할까요? (y/n): ", end="")
        try:
            save_json = input().strip().lower() == "y"
            if save_json:
                products_data = [
                    {
                        "title": p.title,
                        "price": p.price,
                        "product_code": p.product_code,
                        "image_url": p.image_url,
                        "product_url": p.product_url,
                        "description": p.description,
                    }
                    for p in products
                ]
                output = {
                    "url": url,
                    "total_count": len(products),
                    "products": products_data,
                }
                filename = f"products_{url.replace('https://', '').replace('http://', '').replace('/', '_')}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(output, f, ensure_ascii=False, indent=2)
                print(f"  ✅ 저장 완료: {filename}")
        except:
            pass  # 입력 대기 중단 시 무시

    except Exception as e:
        print(f"\n  ❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 범용 상품 파서 테스트 시작\n")

    # 명령줄 인자로 URL 받기
    if len(sys.argv) > 1:
        url = sys.argv[1]
        test_product_parsing_from_url(url)
    else:
        # 기본 테스트 URL들
        print("사용법: python test_product_parser.py <URL>")
        print("\n또는 기본 테스트 URL로 실행:")
        print("-" * 60)

        default_urls = [
            "https://www.musinsa.com",
            "https://ssadagu.kr",
        ]

        for url in default_urls:
            print(f"\n[기본 테스트] {url}")
            try:
                test_product_parsing_from_url(url)
            except KeyboardInterrupt:
                print("\n\n테스트 중단됨")
                break
            except Exception as e:
                print(f"  ❌ 오류: {e}")
                continue

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60 + "\n")
