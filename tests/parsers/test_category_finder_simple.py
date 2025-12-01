"""
간단한 카테고리 탐지 테스트 - 수정된 로직 확인
"""
from parsers.ssadagu.category_finder import find_all_category_paths, print_category_paths
import json

def test_find_categories():
    """
    카테고리 탐지 테스트
    """
    print("카테고리 탐지 시작...")
    paths = find_all_category_paths()
    
    print(f"\n총 {len(paths)}개 경로 발견")
    
    # 잘못된 경로 확인
    invalid_paths = []
    for path in paths:
        if len(path) >= 2:
            # 가전디지털 하위에 남성의류/여성의류가 있으면 잘못된 경로
            if path[0] == "가전디지털" and path[1] in ["남성의류", "여성의류"]:
                invalid_paths.append(path)
            # 문구/오피스 하위에 남성의류/여성의류가 있으면 잘못된 경로
            if path[0] == "문구/오피스" and path[1] in ["남성의류", "여성의류"]:
                invalid_paths.append(path)
    
    if invalid_paths:
        print(f"\n❌ 잘못된 경로 {len(invalid_paths)}개 발견:")
        for path in invalid_paths:
            print(f"  - {' > '.join(path)}")
    else:
        print("\n✓ 잘못된 경로 없음")
    
    # 결과 저장
    output_file = "data/ssadagu/categories_test_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(paths, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_file}")
    
    # 1단계별로 그룹화하여 출력
    print_category_paths(paths)

if __name__ == "__main__":
    test_find_categories()


