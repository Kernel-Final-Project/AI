"""
뷰티 > 스킨케어 경로로 이동 후 상품 10개 크롤링 테스트
"""
from utils.logger import logger
from musinsa_parser.product_crawler import crawl_from_main

def test_crawl_beauty_skincare():
    """뷰티 > 스킨케어 페이지에서 상품 10개 크롤링 테스트"""
    try:
        # 카테고리 경로
        category_path = ["뷰티", "스킨케어"]
        
        logger.info("=" * 80)
        logger.info(f"카테고리 크롤링 테스트: {' > '.join(category_path)}")
        logger.info(f"크롤링할 상품 수: 10개")
        logger.info("=" * 80)
        
        # 크롤링 실행
        products = crawl_from_main(category_path, max_products=10)
        
        if products:
            logger.info(f"\n✓ 성공: {len(products)}개 상품 크롤링 완료\n")
            
            # 상품 정보 출력
            print("\n" + "=" * 80)
            print(f"크롤링된 상품: {len(products)}개")
            print("=" * 80)
            
            for i, product in enumerate(products, 1):
                title = product.get('title', 'N/A')
                price = product.get('price', 'N/A')
                url = product.get('product_url', 'N/A')  # 'url'이 아니라 'product_url'
                product_id = product.get('product_id', 'N/A')
                
                print(f"\n{i}. {title}")
                print(f"   가격: {price}")
                print(f"   ID: {product_id}")
                print(f"   URL: {url[:80] if url != 'N/A' else 'N/A'}...")
            
            print("\n" + "=" * 80)
        else:
            logger.error("✗ 실패: 상품을 크롤링하지 못했습니다")
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_crawl_beauty_skincare()

