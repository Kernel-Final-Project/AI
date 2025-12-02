"""
무신사 카테고리 탐지 테스트 스크립트
"""
# TODO: category_finder 기능이 musinsa_parser에 없음. parsers/musinsa/category_finder.py 참고 필요
# from musinsa_parser.category_crawler import find_all_category_paths, print_category_paths
from utils.logger import logger
import json
from pathlib import Path


def test_category_finder():
    """카테고리 탐지 테스트"""
    logger.info("=" * 80)
    logger.info("무신사 카테고리 탐지 테스트")
    logger.info("=" * 80)
    
    paths = find_all_category_paths()
    
    print("\n" + "=" * 80)
    print(f"총 {len(paths)}개 카테고리 경로 발견")
    print("=" * 80)
    print_category_paths(paths)
    
    # JSON으로 저장
    output_file = Path("data/musinsa/all_categories.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n카테고리 경로를 {output_file}에 저장했습니다")
    
    return paths


if __name__ == "__main__":
    test_category_finder()


