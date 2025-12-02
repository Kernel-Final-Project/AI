"""
1depth → 2depth → 상품 10개 크롤링 테스트
"""
from selenium import webdriver
import traceback

from auto_posting.browser_utils import setup_browser
from musinsa_parser.category_crawler import (
    open_musinsa_category_panel,
    build_top_categories,
    click_1depth_and_get_2depth,
    navigate_to_2depth_category,
)
from musinsa_parser.product_crawler import extract_products_xpath
from utils.logger import logger


def test_1depth_2depth_product_crawl():
    """
    뷰티(id=104) → 스킨케어 → 상품 10개 크롤링 테스트
    """
    print("=" * 80)
    print("1depth → 2depth → 상품 크롤링 테스트 시작")
    print("=" * 80)
    
    driver = None
    
    try:
        driver = setup_browser(headless=False)
        
        # 1) 1depth 카테고리 클릭 (뷰티, id=104)
        print("\n[1] 1depth 카테고리 클릭 및 2depth 목록 가져오기...")
        depth2_categories = click_1depth_and_get_2depth(driver, "104")
        
        if not depth2_categories:
            print("❌ 2depth 카테고리를 찾을 수 없습니다.")
            return
        
        print(f"\n[2] 2depth 카테고리 {len(depth2_categories)}개 발견:")
        for idx, cat in enumerate(depth2_categories[:5], 1):
            print(f"  [{idx}] {cat.name} | url={cat.url}")
        
        # 2) 첫 번째 2depth 카테고리 선택 (스킨케어)
        target_2depth = depth2_categories[0]  # 스킨케어
        print(f"\n[3] 2depth 카테고리 선택: {target_2depth.name}")
        
        # 3) 2depth 카테고리 페이지로 이동
        print(f"[4] 카테고리 페이지로 이동: {target_2depth.url}")
        navigate_to_2depth_category(driver, target_2depth.url)
        
        # 4) 상품 10개 크롤링
        print("\n[5] 상품 10개 크롤링 중...")
        products = extract_products_xpath(driver, limit=10)
        
        # 5) 결과 출력
        print("\n" + "=" * 80)
        print("크롤링 결과")
        print("=" * 80)
        
        if not products:
            print("❌ 상품을 찾을 수 없습니다.")
            return
        
        print(f"\n총 {len(products)}개 상품 추출 완료\n")
        
        for idx, product in enumerate(products, 1):
            print(f"[{idx}] {product.get('product_name', 'N/A')}")
            print(f"    - 가격: {product.get('product_price', 'N/A')}")
            if 'discount_rate' in product:
                print(f"    - 할인율: {product.get('discount_rate', 'N/A')}")
            print(f"    - 이미지: {product.get('image_url', 'N/A')}")
            print(f"    - URL: {product.get('product_url', 'N/A')}")
            print(f"    - 상품코드: {product.get('product_code', 'N/A')}")
            print()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


if __name__ == "__main__":
    test_1depth_2depth_product_crawl()

