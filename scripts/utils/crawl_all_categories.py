"""
모든 카테고리 경로별로 크롤링 실행
"""
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from ssadagu_parser.crawler import crawl_from_main
from utils.logger import logger


def load_categories(file_path: str = "data/ssadagu/all_categories_final.json") -> List[List[str]]:
    """
    카테고리 경로 파일 로드
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        logger.info(f"카테고리 경로 로드 완료: {len(categories)}개")
        return categories
    except Exception as e:
        logger.error(f"카테고리 경로 로드 실패: {e}")
        return []


def save_crawl_result(category_path: List[str], products: List[Dict], output_dir: str = "data/ssadagu/crawl_results"):
    """
    크롤링 결과를 파일로 저장
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 파일명 생성 (카테고리 경로를 파일명으로)
    safe_filename = "_".join(category_path).replace("/", "_").replace(" ", "_")
    file_path = Path(output_dir) / f"{safe_filename}.json"
    
    result = {
        "category_path": category_path,
        "crawl_time": datetime.now().isoformat(),
        "product_count": len(products),
        "products": products
    }
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"결과 저장 완료: {file_path} ({len(products)}개 상품)")
        return file_path
    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
        return None


def crawl_all_categories(
    categories: List[List[str]],
    max_products_per_category: int = 100,
    start_from: int = 0,
    delay_between_categories: float = 2.0
):
    """
    모든 카테고리 경로에 대해 크롤링 실행
    
    Args:
        categories: 카테고리 경로 리스트
        max_products_per_category: 카테고리당 최대 수집 상품 수
        start_from: 시작 인덱스 (중단 후 재개 시 사용)
        delay_between_categories: 카테고리 간 대기 시간 (초)
    """
    total = len(categories)
    logger.info(f"총 {total}개 카테고리 크롤링 시작 (시작 인덱스: {start_from})")
    
    success_count = 0
    fail_count = 0
    total_products = 0
    
    # 진행 상황 저장 파일
    progress_file = Path("data/ssadagu/crawl_progress.json")
    
    for i, category_path in enumerate(categories[start_from:], start=start_from):
        category_str = " > ".join(category_path)
        logger.info(f"\n{'=' * 80}")
        logger.info(f"[{i+1}/{total}] 카테고리: {category_str}")
        logger.info(f"{'=' * 80}")
        
        try:
            # 크롤링 실행
            products = crawl_from_main(category_path, max_products=max_products_per_category)
            
            if products:
                # 결과 저장
                save_crawl_result(category_path, products)
                success_count += 1
                total_products += len(products)
                logger.info(f"✅ 성공: {len(products)}개 상품 수집")
            else:
                logger.warning(f"⚠️  상품 없음: {category_str}")
                fail_count += 1
            
            # 진행 상황 저장
            progress = {
                "last_index": i,
                "success_count": success_count,
                "fail_count": fail_count,
                "total_products": total_products,
                "last_update": datetime.now().isoformat()
            }
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            
            # 다음 카테고리로 넘어가기 전 대기
            if i < total - 1:
                time.sleep(delay_between_categories)
                
        except Exception as e:
            logger.error(f"❌ 크롤링 실패: {category_str} - {e}")
            fail_count += 1
            import traceback
            logger.error(traceback.format_exc())
            
            # 에러가 발생해도 계속 진행
            continue
    
    # 최종 결과
    logger.info(f"\n{'=' * 80}")
    logger.info("크롤링 완료")
    logger.info(f"{'=' * 80}")
    logger.info(f"총 카테고리: {total}개")
    logger.info(f"성공: {success_count}개")
    logger.info(f"실패: {fail_count}개")
    logger.info(f"총 수집 상품: {total_products}개")
    logger.info(f"{'=' * 80}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="모든 카테고리 경로별 크롤링")
    parser.add_argument("--max-products", type=int, default=100, help="카테고리당 최대 상품 수 (기본값: 100)")
    parser.add_argument("--start-from", type=int, default=0, help="시작 인덱스 (기본값: 0)")
    parser.add_argument("--delay", type=float, default=2.0, help="카테고리 간 대기 시간 초 (기본값: 2.0)")
    parser.add_argument("--categories-file", type=str, default="data/ssadagu/all_categories_valid.json", help="카테고리 파일 경로")
    
    args = parser.parse_args()
    
    # 카테고리 로드
    categories = load_categories(args.categories_file)
    
    if not categories:
        logger.error("카테고리 경로를 로드할 수 없습니다.")
        exit(1)
    
    # 크롤링 시작
    crawl_all_categories(
        categories=categories,
        max_products_per_category=args.max_products,
        start_from=args.start_from,
        delay_between_categories=args.delay
    )

