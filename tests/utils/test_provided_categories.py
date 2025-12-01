"""
사용자가 제공한 카테고리 경로로 크롤링 테스트
"""
from parsers.ssadagu.crawler import crawl_from_main
from parsers.ssadagu.categories import USER_PROVIDED_CATEGORIES

if __name__ == "__main__":
    print("=" * 60)
    print("사용자 제공 카테고리 경로 크롤링 테스트")
    print("=" * 60)
    print(f"총 {len(USER_PROVIDED_CATEGORIES)}개 카테고리\n")
    
    # 처음 3개만 테스트
    test_categories = USER_PROVIDED_CATEGORIES[:3]
    
    for i, category_path in enumerate(test_categories, 1):
        print(f"\n[{i}/{len(test_categories)}] {' > '.join(category_path)}")
        print("-" * 60)
        
        try:
            products = crawl_from_main(category_path, max_products=5)
            print(f"✅ 성공: {len(products)}개 상품 수집")
            
            if products:
                print(f"   첫 번째 상품: {products[0]['title'][:60]}...")
        except Exception as e:
            print(f"❌ 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)



