"""
탐지한 카테고리 경로를 자동으로 크롤링하는 모듈
"""
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from tqdm import tqdm

from ssadagu_parser.category_finder import find_all_category_paths
from ssadagu_parser.crawler import crawl_from_main
from utils.logger import logger


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


def save_all_results_to_json(all_results: Dict, output_file: str):
    """
    모든 크롤링 결과를 하나의 JSON 파일로 저장 (무신사 형식)
    
    Args:
        all_results: 모든 카테고리별 크롤링 결과 딕셔너리
        output_file: 출력 파일 경로
    """
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    total_categories = len(all_results)
    total_products = sum(
        cat_data.get("product_count", 0) 
        for cat_data in all_results.values()
    )
    
    output_data = {
        "crawl_date": datetime.now().isoformat(),
        "total_categories": total_categories,
        "total_products": total_products,
        "categories": all_results
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 전체 결과 JSON 저장 완료: {output_file}")
        logger.info(f"  - 총 카테고리: {total_categories}개")
        logger.info(f"  - 총 상품: {total_products}개")
        return output_file
    except Exception as e:
        logger.error(f"❌ 결과 저장 실패: {e}")
        return None


def auto_crawl_all_categories(
    max_products_per_category: int = 10,
    delay_between_categories: float = 2.0,
    start_from: int = 0,
    save_results: bool = True
):
    """
    카테고리 경로를 자동으로 탐지하고 모든 경로에 대해 크롤링 실행
    
    Args:
        max_products_per_category: 카테고리당 최대 수집 상품 수
        delay_between_categories: 카테고리 간 대기 시간 (초)
        start_from: 시작 인덱스 (중단 후 재개 시 사용)
        save_results: 결과를 파일로 저장할지 여부
    """
    logger.info("=" * 80)
    logger.info("카테고리 자동 탐지 및 크롤링 시작")
    logger.info("=" * 80)
    
    # 1. 카테고리 경로 탐지
    logger.info("1단계: 카테고리 경로 탐지 중...")
    category_paths = find_all_category_paths()
    
    if not category_paths:
        logger.error("카테고리 경로를 찾을 수 없습니다.")
        return
    
    total = len(category_paths)
    logger.info(f"총 {total}개 카테고리 경로 발견")
    
    # 2. 크롤링 실행
    logger.info("2단계: 크롤링 시작...")
    logger.info("=" * 80)
    
    success_count = 0
    fail_count = 0
    total_products = 0
    
    # 전체 결과 저장용 딕셔너리 (무신사 형식)
    all_results = {}
    
    # 진행 상황 저장 파일
    progress_file = Path("data/ssadagu/crawl_progress.json")
    Path(progress_file.parent).mkdir(parents=True, exist_ok=True)
    
    # tqdm으로 진행률 표시
    with tqdm(
        total=total,
        initial=start_from,
        desc="크롤링 진행",
        unit="카테고리",
        ncols=100,
        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
    ) as pbar:
        for i, category_path in enumerate(category_paths[start_from:], start=start_from):
            category_str = " > ".join(category_path)
            
            # 로그 출력
            logger.info(f"\n{'=' * 80}")
            logger.info(f"[{i+1}/{total}] 카테고리: {category_str}")
            logger.info(f"{'=' * 80}")
            
            try:
                # 크롤링 실행
                products = crawl_from_main(category_path, max_products=max_products_per_category)
                
                # 카테고리 키 생성 (무신사 형식: "카테고리1 > 카테고리2")
                category_key = " > ".join(category_path)
                
                if products:
                    # 전체 결과에 추가
                    all_results[category_key] = {
                        "category_path": category_path,
                        "product_count": len(products),
                        "products": products
                    }
                    
                    success_count += 1
                    total_products += len(products)
                    logger.info(f"✅ 성공: {len(products)}개 상품 수집")
                    pbar.set_postfix({
                        '성공': success_count,
                        '실패': fail_count,
                        '상품': total_products
                    })
                else:
                    # 상품이 없어도 결과에 추가
                    all_results[category_key] = {
                        "category_path": category_path,
                        "product_count": 0,
                        "products": []
                    }
                    logger.warning(f"⚠️  상품 없음: {category_str}")
                    fail_count += 1
                    pbar.set_postfix({
                        '성공': success_count,
                        '실패': fail_count,
                        '상품': total_products
                    })
                
                # 진행 상황 저장
                progress = {
                    "last_index": i,
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_products": total_products,
                    "last_update": datetime.now().isoformat(),
                    "total_categories": total
                }
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False, indent=2)
                
                # 다음 카테고리로 넘어가기 전 대기
                if i < total - 1:
                    time.sleep(delay_between_categories)
                    
            except Exception as e:
                # 에러 발생 시에도 결과에 추가 (빈 상품 리스트)
                category_key = " > ".join(category_path)
                all_results[category_key] = {
                    "category_path": category_path,
                    "product_count": 0,
                    "products": []
                }
                
                logger.error(f"❌ 크롤링 실패: {category_str} - {e}")
                fail_count += 1
                import traceback
                logger.error(traceback.format_exc())
                pbar.set_postfix({
                    '성공': success_count,
                    '실패': fail_count,
                    '상품': total_products
                })
                # 에러가 발생해도 계속 진행
                continue
            finally:
                # 진행률 업데이트
                pbar.update(1)
    
    # 최종 결과
    logger.info(f"\n{'=' * 80}")
    logger.info("크롤링 완료")
    logger.info(f"{'=' * 80}")
    logger.info(f"총 카테고리: {total}개")
    logger.info(f"성공: {success_count}개")
    logger.info(f"실패: {fail_count}개")
    logger.info(f"총 수집 상품: {total_products}개")
    logger.info(f"{'=' * 80}")
    
    # 전체 결과를 하나의 JSON 파일로 저장 (무신사 형식)
    if save_results and all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/ssadagu/crawl_{timestamp}.json"
        save_all_results_to_json(all_results, output_file)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="카테고리 자동 탐지 및 크롤링")
    parser.add_argument("--max-products", type=int, default=10, help="카테고리당 최대 상품 수 (기본값: 10)")
    parser.add_argument("--start-from", type=int, default=0, help="시작 인덱스 (기본값: 0)")
    parser.add_argument("--delay", type=float, default=2.0, help="카테고리 간 대기 시간 초 (기본값: 2.0)")
    parser.add_argument("--no-save", action="store_true", help="결과를 파일로 저장하지 않음")
    
    args = parser.parse_args()
    
    # 크롤링 시작
    auto_crawl_all_categories(
        max_products_per_category=args.max_products,
        delay_between_categories=args.delay,
        start_from=args.start_from,
        save_results=not args.no_save
    )

