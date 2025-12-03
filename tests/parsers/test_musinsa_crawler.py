"""
무신사 크롤러 테스트 스크립트
"""
from musinsa_parser.product_crawler import crawl_from_main, crawl_category_page as crawl_category
from utils.logger import logger


def test_single_category():
    """단일 카테고리 크롤링 테스트"""
    logger.info("=" * 80)
    logger.info("무신사 단일 카테고리 크롤링 테스트")
    logger.info("=" * 80)
    
    # 테스트 카테고리: ["뷰티", "스킨케어"]
    category_path = ["뷰티", "스킨케어"]
    
    products = crawl_from_main(category_path, max_products=10)
    
    logger.info(f"\n수집된 상품 수: {len(products)}개")
    
    if products:
        logger.info("\n첫 번째 상품 정보:")
        first_product = products[0]
        for key, value in first_product.items():
            logger.info(f"  {key}: {value}")
    
    return products


def test_direct_url():
    """직접 URL로 크롤링 테스트"""
    logger.info("=" * 80)
    logger.info("무신사 직접 URL 크롤링 테스트")
    logger.info("=" * 80)
    
    # 테스트 URL (뷰티 > 스킨케어 카테고리)
    # 실제 URL은 크롤러가 찾아야 함
    # category_url = "https://www.musinsa.com/categories/item/..."
    
    # products = crawl_category(category_url, max_products=10)
    # logger.info(f"\n수집된 상품 수: {len(products)}개")
    
    logger.info("직접 URL 테스트는 카테고리 URL을 먼저 확인해야 합니다")
    return []


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "url":
            test_direct_url()
        else:
            test_single_category()
    else:
        test_single_category()


