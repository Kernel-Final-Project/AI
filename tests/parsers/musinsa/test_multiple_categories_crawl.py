"""
여러 카테고리별로 각각 10개씩 상품 크롤링 테스트
"""
from selenium import webdriver
import traceback
import json
from datetime import datetime
import os

from auto_posting.browser_utils import setup_browser
from musinsa_parser.category_crawler import (
    build_top_categories,
    click_1depth_and_get_2depth,
    navigate_to_2depth_category,
)
from musinsa_parser.product_crawler import extract_products_xpath
from utils.logger import logger


def test_multiple_categories_crawl():
    """
    여러 카테고리별로 각각 10개씩 상품 크롤링
    """
    print("=" * 80)
    print("여러 카테고리별 상품 크롤링 테스트 시작")
    print("=" * 80)
    
    # 테스트할 카테고리 목록 (1depth, 2depth)
    test_categories = [
        ["뷰티", "스킨케어"],
        ["뷰티", "마스크팩"],
        ["상의", "티셔츠"],
        ["아우터", "자켓"],
        ["신발", "스니커즈"],
    ]
    
    driver = None
    
    try:
        driver = setup_browser(headless=False)
        
        # 1depth 카테고리 목록 가져오기
        print("\n[1] 1depth 카테고리 목록 가져오기...")
        top_categories = build_top_categories(driver)
        
        if not top_categories:
            print("❌ 1depth 카테고리를 찾을 수 없습니다.")
            return
        
        print(f"1depth 카테고리 {len(top_categories)}개 발견")
        
        all_results = {}
        
        # 각 카테고리별로 크롤링
        for category_path in test_categories:
            _1depth_name = category_path[0]
            _2depth_name = category_path[1]
            category_path_str = " > ".join(category_path)
            
            print(f"\n{'=' * 80}")
            print(f"카테고리: {category_path_str}")
            print(f"{'=' * 80}")
            
            try:
                # 1depth 카테고리 찾기
                _1depth_node = next(
                    (node for node in top_categories 
                     if node.name == _1depth_name and node.depth == 1),
                    None
                )
                
                if not _1depth_node:
                    print(f"❌ 1depth 카테고리 '{_1depth_name}'를 찾을 수 없습니다.")
                    all_results[category_path_str] = []
                    continue
                
                # 1depth 클릭 후 2depth 목록 가져오기
                depth2_categories = click_1depth_and_get_2depth(
                    driver, _1depth_node.category_id
                )
                
                if not depth2_categories:
                    print(f"❌ 2depth 카테고리를 찾을 수 없습니다.")
                    all_results[category_path_str] = []
                    continue
                
                # 2depth 카테고리 찾기
                _2depth_node = next(
                    (node for node in depth2_categories 
                     if node.name == _2depth_name and node.depth == 2),
                    None
                )
                
                if not _2depth_node or not _2depth_node.url:
                    print(f"❌ 2depth 카테고리 '{_2depth_name}'를 찾을 수 없거나 URL이 없습니다.")
                    all_results[category_path_str] = []
                    continue
                
                # 2depth 카테고리 페이지로 이동
                print(f"[2] 카테고리 페이지로 이동: {_2depth_node.url}")
                navigate_to_2depth_category(driver, _2depth_node.url)
                
                # 상품 10개 크롤링
                print(f"[3] 상품 10개 크롤링 중...")
                products = extract_products_xpath(driver, limit=10)
                
                all_results[category_path_str] = products
                
                print(f"✅ {len(products)}개 상품 추출 완료")
                
            except Exception as e:
                print(f"❌ 카테고리 '{category_path_str}' 크롤링 중 오류: {e}")
                traceback.print_exc()
                all_results[category_path_str] = []
        
        # 전체 결과 출력
        print("\n" + "=" * 80)
        print("전체 크롤링 결과 요약")
        print("=" * 80)
        
        total_products = 0
        for category_path_str, products in all_results.items():
            print(f"\n[{category_path_str}]")
            print(f"  추출된 상품: {len(products)}개")
            if products:
                print(f"  샘플 상품:")
                for idx, product in enumerate(products[:3], 1):
                    print(f"    {idx}. {product.get('product_name', 'N/A')} - {product.get('product_price', 'N/A')}")
            total_products += len(products)
        
        print(f"\n총 {len(all_results)}개 카테고리에서 {total_products}개 상품 추출 완료")
        
        # JSON 파일로 저장
        output_dir = "data/musinsa"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"products_multiple_categories_{timestamp}.json")
        
        # 카테고리별로 구조화된 데이터
        output_data = {
            "crawl_date": datetime.now().isoformat(),
            "total_categories": len(all_results),
            "total_products": total_products,
            "categories": []
        }
        
        for category_path_str, products in all_results.items():
            category_data = {
                "category_path": category_path_str.split(" > "),
                "product_count": len(products),
                "products": products
            }
            output_data["categories"].append(category_data)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 결과를 JSON 파일로 저장: {output_file}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


if __name__ == "__main__":
    test_multiple_categories_crawl()

