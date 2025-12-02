"""
카테고리 네비게이션 크롤링 테스트 스크립트
"""
import sys
# TODO: category_navigator는 parsers/base에 없음. 별도 구현 필요 또는 주석 처리
# from scraper.category_navigator import crawl_all_categories
from utils.logger import logger

# 로그 레벨을 WARNING으로 설정
import logging
logging.getLogger('ai_blog_project').setLevel(logging.WARNING)


def test_category_crawling(url: str, max_categories: int = 3):
    """
    카테고리 크롤링 테스트
    
    Args:
        url: 메인 페이지 URL
        max_categories: 테스트할 최대 카테고리 수
    """
    print("\n" + "="*80)
    print("카테고리 네비게이션 크롤링 테스트")
    print("="*80)
    print(f"\n[입력 URL] {url}")
    print(f"[최대 카테고리 수] {max_categories}개\n")
    
    try:
        # 카테고리 크롤링
        print("🚀 카테고리 크롤링 시작...\n")
        products = crawl_all_categories(
            url=url,
            max_categories=max_categories,
            use_hover=False,  # hover 필요 시 True로 변경
            headless=True
        )
        
        print(f"\n{'='*80}")
        print("📊 크롤링 결과")
        print(f"{'='*80}\n")
        print(f"✅ 총 상품 수: {len(products)}개\n")
        
        if len(products) == 0:
            print("⚠️  상품을 찾을 수 없습니다.")
            return
        
        # 상품 정보 출력 (처음 10개)
        print(f"{'─'*80}")
        print("추출된 상품 정보 (처음 10개)")
        print(f"{'─'*80}\n")
        
        for i, product in enumerate(products[:10], 1):
            print(f"[상품 {i}]")
            print(f"  📌 제목: {product.title[:60]}...")
            if product.price:
                print(f"  💰 가격: {product.price}")
            if product.product_code:
                print(f"  🔢 상품 코드: {product.product_code}")
            if product.product_url:
                print(f"  🔗 링크: {product.product_url[:60]}...")
            print()
        
        if len(products) > 10:
            print(f"  ... 외 {len(products) - 10}개 상품\n")
        
        # 통계
        print(f"{'─'*80}")
        print("통계")
        print(f"{'─'*80}\n")
        price_count = sum(1 for p in products if p.price)
        code_count = sum(1 for p in products if p.product_code)
        image_count = sum(1 for p in products if p.image_url)
        link_count = sum(1 for p in products if p.product_url)
        
        print(f"  💰 가격 정보: {price_count}개 ({price_count/len(products)*100:.1f}%)")
        print(f"  🔢 상품 코드: {code_count}개 ({code_count/len(products)*100:.1f}%)")
        print(f"  🖼️  이미지 URL: {image_count}개 ({image_count/len(products)*100:.1f}%)")
        print(f"  🔗 상품 링크: {link_count}개 ({link_count/len(products)*100:.1f}%)")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 카테고리 크롤링 테스트 시작\n")
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        max_cat = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        test_category_crawling(url, max_cat)
    else:
        print("사용법: python test_category_crawler.py <URL> [최대_카테고리_수]")
        print("\n예시:")
        print("  python test_category_crawler.py https://ssadagu.kr 3")
    
    print("\n" + "="*80)
    print("테스트 완료")
    print("="*80 + "\n")


