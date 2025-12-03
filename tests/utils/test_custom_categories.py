"""
사용자가 지정한 카테고리 경로로 크롤링 테스트
"""
from ssadagu_parser.crawler import crawl_from_main

if __name__ == "__main__":
    print("=" * 60)
    print("사용자 지정 카테고리 크롤링 테스트")
    print("=" * 60)
    
    # 사용자가 알려준 카테고리 경로들
    categories = [
        ["패션의류/이너웨어", "남성의류", "셔츠"],
        ["패션의류/이너웨어", "남성의류", "티셔츠"],
        ["패션의류/이너웨어", "여성의류", "블라우스"],
        # 여기에 원하는 카테고리 경로를 추가하세요
        # ["신발/가방/패션잡화", "여성슈즈", "운동화"],
        # ["스포츠/레저", "스포츠용품", "요가복"],
    ]
    
    all_products = []
    
    for i, category_path in enumerate(categories, 1):
        print(f"\n[{i}/{len(categories)}] 카테고리: {' > '.join(category_path)}")
        print("-" * 60)
        
        products = crawl_from_main(category_path, max_products=10)
        print(f"수집된 상품: {len(products)}개")
        
        if products:
            print(f"  첫 번째 상품: {products[0]['title'][:50]}...")
            all_products.extend(products)
    
    print("\n" + "=" * 60)
    print(f"총 {len(all_products)}개 상품 수집 완료")
    print("=" * 60)



