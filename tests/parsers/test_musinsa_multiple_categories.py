"""
여러 카테고리를 카테고리 이름으로 테스트
하드코딩된 경로 없이 카테고리 이름만으로 크롤링 테스트
"""
from utils.logger import logger
from musinsa_parser.product_crawler import crawl_from_main
# TODO: category_finder 기능이 musinsa_parser에 없음. parsers/musinsa/category_finder.py 참고 필요
# from musinsa_parser.category_crawler import (
#     find_category_path_by_names,
#     load_category_paths,
#     save_category_paths,
#     find_all_category_paths
# )


def print_summary(results: list):
    """
    테스트 결과 요약 출력
    
    Args:
        results: 테스트 결과 리스트
    """
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    print(f"\n총 {total_count}개 카테고리 테스트")
    print(f"성공: {success_count}개")
    print(f"실패: {total_count - success_count}개")
    print("\n" + "-" * 80)
    
    for i, result in enumerate(results, 1):
        category = result["category"]
        success = result["success"]
        products_count = len(result["products"])
        path = result["path"]
        
        status = "✓" if success else "✗"
        print(f"\n{i}. {status} {category}")
        if path:
            print(f"   경로: {' > '.join(path)}")
            print(f"   크롤링된 상품: {products_count}개")
            
            # 샘플 상품 정보 출력 (최대 3개)
            if products_count > 0:
                print("   샘플 상품:")
                for j, product in enumerate(result["products"][:3], 1):
                    title = product.get('title', 'N/A')
                    price = product.get('price', 'N/A')
                    print(f"     {j}. {title[:50]}... - {price}")
        else:
            print(f"   경로를 찾을 수 없습니다")
    
    print("\n" + "=" * 80)


def test_categories_by_name(
    category_list: list,
    max_products: int = 10,
    auto_generate: bool = True
):
    """
    카테고리 이름 튜플 리스트로 테스트
    
    Args:
        category_list: 카테고리 이름 튜플 리스트
                      예: [("신발", "스니커즈"), ("상의", "티셔츠")]
        max_products: 각 카테고리당 최대 크롤링할 상품 수
        auto_generate: 카테고리 경로 파일이 없을 때 자동 생성 여부
    """
    logger.info("=" * 80)
    logger.info("여러 카테고리 크롤링 테스트 시작")
    logger.info(f"테스트할 카테고리: {len(category_list)}개")
    logger.info(f"각 카테고리당 최대 상품 수: {max_products}개")
    logger.info("=" * 80)
    
    # 1. 카테고리 경로 로드 (없으면 생성)
    all_paths = load_category_paths()
    if not all_paths:
        if auto_generate:
            logger.info("카테고리 경로 파일이 없습니다. 자동 생성 중...")
            all_paths = find_all_category_paths()
            if all_paths:
                save_category_paths(all_paths)
                logger.info(f"카테고리 경로 {len(all_paths)}개를 생성했습니다")
            else:
                logger.error("카테고리 경로 생성 실패")
                return []
        else:
            logger.error("카테고리 경로 파일이 없습니다. 먼저 카테고리 경로를 생성해주세요.")
            return []
    
    # 2. 각 카테고리 테스트
    results = []
    
    for main, sub in category_list:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"카테고리 테스트: {main} > {sub}")
        logger.info(f"{'=' * 80}")
        
        try:
            # 경로 찾기
            matching_paths = find_category_path_by_names(main, sub, all_paths)
            
            if not matching_paths:
                logger.warning(f"카테고리 경로를 찾을 수 없습니다: {main} > {sub}")
                results.append({
                    "category": f"{main} > {sub}",
                    "path": None,
                    "products": [],
                    "success": False
                })
                continue
            
            # 첫 번째 매칭 경로 사용
            path = matching_paths[0]
            logger.info(f"찾은 경로: {' > '.join(path)}")
            
            # 크롤링 실행
            products = crawl_from_main(path, max_products=max_products)
            
            success = len(products) > 0
            results.append({
                "category": f"{main} > {sub}",
                "path": path,
                "products": products,
                "success": success
            })
            
            if success:
                logger.info(f"✓ 성공: {len(products)}개 상품 크롤링 완료")
            else:
                logger.warning(f"✗ 실패: 상품을 크롤링하지 못했습니다")
                
        except Exception as e:
            logger.error(f"카테고리 테스트 중 오류 ({main} > {sub}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            results.append({
                "category": f"{main} > {sub}",
                "path": None,
                "products": [],
                "success": False
            })
    
    # 3. 결과 출력
    print_summary(results)
    
    return results


if __name__ == "__main__":
    # 테스트할 카테고리 목록
    # (메인 카테고리, 서브 카테고리) 튜플 리스트
    test_categories = [
        ("뷰티", "스킨케어"),      # 이미 테스트 완료된 카테고리
        ("신발", "스니커즈"),
        ("상의", "티셔츠"),
        ("아우터", "자켓"),
        ("가방", "백팩")
    ]
    
    # 테스트 실행
    test_categories_by_name(test_categories, max_products=10)

