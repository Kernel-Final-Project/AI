"""
무신사 전체 카테고리 탐색 및 상품 크롤링 스크립트
1. 모든 1depth, 2depth 카테고리 탐색 → JSON 저장
2. 저장된 카테고리로 각 카테고리별 상품 크롤링 → JSON 저장
"""
import json
import os
from datetime import datetime
from typing import List, Dict
import traceback

from auto_posting.browser_utils import setup_browser
from musinsa_parser.category_crawler import (
    build_top_categories,
    click_1depth_and_get_2depth,
)
from musinsa_parser.product_crawler import extract_products_xpath
from musinsa_parser.category_crawler import navigate_to_2depth_category
import time
from musinsa_parser.category_node import CategoryNode
from utils.logger import logger


def crawl_all_categories() -> Dict:
    """
    모든 1depth, 2depth 카테고리 탐색
    
    Returns:
        카테고리 구조 딕셔너리
    """
    print("=" * 80)
    print("전체 카테고리 탐색 시작")
    print("=" * 80)
    
    driver = None
    all_categories = {}
    
    try:
        driver = setup_browser(headless=False)
        
        # 1depth 카테고리 가져오기
        print("\n[1] 1depth 카테고리 탐색 중...")
        top_categories = build_top_categories(driver)
        
        if not top_categories:
            print("❌ 1depth 카테고리를 찾을 수 없습니다.")
            return {}
        
        print(f"✅ 1depth 카테고리 {len(top_categories)}개 발견")
        
        # 각 1depth 카테고리의 2depth 탐색
        for idx, _1depth_node in enumerate(top_categories, 1):
            if _1depth_node.depth != 1:
                continue
                
            print(f"\n[{idx}/{len(top_categories)}] 1depth: {_1depth_node.name} (id={_1depth_node.category_id})")
            
            try:
                # 2depth 카테고리 가져오기
                depth2_categories = click_1depth_and_get_2depth(
                    driver, _1depth_node.category_id
                )
                
                all_categories[_1depth_node.name] = {
                    "category_id": _1depth_node.category_id,
                    "url": _1depth_node.url,
                    "depth": 1,
                    "subcategories": []
                }
                
                for _2depth_node in depth2_categories:
                    all_categories[_1depth_node.name]["subcategories"].append({
                        "name": _2depth_node.name,
                        "category_id": _2depth_node.category_id,
                        "url": _2depth_node.url,
                        "depth": 2,
                    })
                
                print(f"  ✅ 2depth 카테고리 {len(depth2_categories)}개 발견")
                
            except Exception as e:
                print(f"  ❌ 2depth 카테고리 탐색 실패: {e}")
                all_categories[_1depth_node.name] = {
                    "category_id": _1depth_node.category_id,
                    "url": _1depth_node.url,
                    "depth": 1,
                    "subcategories": []
                }
                continue
        
        print(f"\n✅ 전체 카테고리 탐색 완료")
        print(f"  - 1depth: {len(all_categories)}개")
        total_2depth = sum(len(cat["subcategories"]) for cat in all_categories.values())
        print(f"  - 2depth: {total_2depth}개")
        
        return all_categories
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
        return {}
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


def save_categories_to_json(categories: Dict, output_file: str):
    """
    카테고리 구조를 JSON 파일로 저장
    
    Args:
        categories: 카테고리 딕셔너리
        output_file: 출력 파일 경로
    """
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    data = {
        "crawl_date": datetime.now().isoformat(),
        "total_1depth": len(categories),
        "total_2depth": sum(len(cat["subcategories"]) for cat in categories.values()),
        "categories": categories
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 카테고리 JSON 저장 완료: {output_file}")


def crawl_products_from_categories(categories_file: str, max_products_per_category: int = 10):
    """
    저장된 카테고리 파일을 읽어서 각 카테고리별 상품 크롤링
    
    Args:
        categories_file: 카테고리 JSON 파일 경로
        max_products_per_category: 카테고리별 최대 상품 개수
    """
    print("=" * 80)
    print("카테고리별 상품 크롤링 시작")
    print("=" * 80)
    
    # 카테고리 파일 읽기
    with open(categories_file, "r", encoding="utf-8") as f:
        categories_data = json.load(f)
    
    categories = categories_data.get("categories", {})
    
    driver = None
    all_results = {}
    total_crawled = 0
    
    try:
        driver = setup_browser(headless=False)
        
        for _1depth_name, _1depth_data in categories.items():
            subcategories = _1depth_data.get("subcategories", [])
            
            if not subcategories:
                print(f"\n⚠️  {_1depth_name}: 2depth 카테고리 없음, 건너뜀")
                continue
            
            print(f"\n{'=' * 80}")
            print(f"1depth: {_1depth_name} ({len(subcategories)}개 2depth 카테고리)")
            print(f"{'=' * 80}")
            
            for idx, _2depth_data in enumerate(subcategories, 1):
                _2depth_name = _2depth_data["name"]
                _2depth_url = _2depth_data["url"]
                category_path_str = f"{_1depth_name} > {_2depth_name}"
                
                print(f"\n[{idx}/{len(subcategories)}] {category_path_str}")
                
                try:
                    # 카테고리 페이지로 이동
                    navigate_to_2depth_category(driver, _2depth_url)
                    
                    # 상품 크롤링
                    products = extract_products_xpath(driver, limit=max_products_per_category)
                    
                    all_results[category_path_str] = {
                        "category_path": [_1depth_name, _2depth_name],
                        "category_url": _2depth_url,
                        "product_count": len(products),
                        "products": products
                    }
                    
                    total_crawled += len(products)
                    print(f"  ✅ {len(products)}개 상품 추출 완료")
                    
                except Exception as e:
                    print(f"  ❌ 크롤링 실패: {e}")
                    all_results[category_path_str] = {
                        "category_path": [_1depth_name, _2depth_name],
                        "category_url": _2depth_url,
                        "product_count": 0,
                        "products": []
                    }
                    continue
        
        print(f"\n✅ 전체 크롤링 완료")
        print(f"  - 총 카테고리: {len(all_results)}개")
        print(f"  - 총 상품: {total_crawled}개")
        
        # JSON 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/musinsa/products_all_categories_{timestamp}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        output_data = {
            "crawl_date": datetime.now().isoformat(),
            "total_categories": len(all_results),
            "total_products": total_crawled,
            "categories": all_results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 상품 JSON 저장 완료: {output_file}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


def main():
    """
    메인 실행 함수
    1. 전체 카테고리 탐색 및 저장
    2. 저장된 카테고리로 상품 크롤링 및 저장
    """
    # 1. 카테고리 탐색 및 저장
    categories = crawl_all_categories()
    
    if not categories:
        print("❌ 카테고리 탐색 실패")
        return
    
    # 카테고리 JSON 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    categories_file = f"data/musinsa/all_categories_{timestamp}.json"
    save_categories_to_json(categories, categories_file)
    
    # 2. 상품 크롤링 (자동 진행)
    print("\n" + "=" * 80)
    print("카테고리별 상품 크롤링을 자동으로 시작합니다...")
    max_products = 10  # 기본값
    crawl_products_from_categories(categories_file, max_products_per_category=max_products)


if __name__ == "__main__":
    main()

