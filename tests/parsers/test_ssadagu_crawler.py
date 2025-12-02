"""
싸다구 크롤러 테스트
"""
from ssadagu_parser.crawler import crawl_from_main, crawl_category

if __name__ == "__main__":
    print("=" * 60)
    print("싸다구 크롤러 테스트")
    print("=" * 60)
    
    # 방법 1: 메인 페이지에서 카테고리 경로로 이동
    print("\n[방법 1] 메인 페이지에서 카테고리 경로로 이동")
    print("-" * 60)
    # 카테고리 경로: 전체카테고리 > 패션의류/이너웨어 > 남성의류 > 티셔츠
    category_path = ["패션의류/이너웨어", "남성의류", "티셔츠"]
    print(f"카테고리 경로: {' > '.join(category_path)}\n")
    
    products = crawl_from_main(category_path, max_products=20)
    
    print(f"\n수집된 상품: {len(products)}개\n")
    
    if products:
        print("=" * 60)
        print("상위 5개 상품 정보")
        print("=" * 60)
        for i, product in enumerate(products[:5], 1):
            print(f"\n[상품 {i}]")
            print(f"  제목: {product['title']}")
            print(f"  가격: {product['price']}")
            print(f"  이미지: {product['image_url'][:80]}..." if len(product['image_url']) > 80 else f"  이미지: {product['image_url']}")
            print(f"  링크: {product['product_url']}")
            print(f"  상품ID: {product['product_id']}")
    else:
        print("수집된 상품이 없습니다.")
    
    # 방법 2: 직접 URL로 크롤링 (기존 방식)
    # print("\n[방법 2] 직접 URL로 크롤링")
    # print("-" * 60)
    # category_url = "https://ssadagu.kr/shop/search.php?ss_tx=%EB%82%A8%EC%84%B1+%EC%85%94%EC%B8%A0"
    # products = crawl_category(category_url, max_products=20)

