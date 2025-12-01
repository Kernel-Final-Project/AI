"""
올바른 카테고리 경로만 필터링
"""
import json
from parsers.ssadagu.categories import USER_PROVIDED_CATEGORIES

# 올바른 1단계 카테고리 목록
VALID_LEVEL1 = [
    "패션의류/이너웨어",
    "신발/가방/패션잡화",
    "스포츠/레저",
    "홈인테리어",
    "펫 용품",
    "생활용품",
    "자동차용품",
    "문구/오피스",
    "주방용품",
    "가전디지털",
    "유아용품",
    "완구/취미",
]

def is_valid_category_path(path: list) -> bool:
    """
    카테고리 경로가 유효한지 확인
    """
    if not path or len(path) == 0:
        return False
    
    # 1단계가 유효한 카테고리인지 확인
    if path[0] not in VALID_LEVEL1:
        return False
    
    # 잘못된 조합 필터링
    invalid_combinations = [
        # 가전디지털 하위에 남성의류/여성의류가 있을 수 없음
        ("가전디지털", "남성의류"),
        ("가전디지털", "여성의류"),
        ("가전디지털", "이너웨어/파자마"),
        # 다른 잘못된 조합들도 추가 가능
    ]
    
    if len(path) >= 2:
        for invalid in invalid_combinations:
            if path[0] == invalid[0] and path[1] == invalid[1]:
                return False
    
    return True

def filter_categories(input_file: str, output_file: str):
    """
    카테고리 파일에서 유효한 경로만 필터링
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        all_categories = json.load(f)
    
    # 사용자가 제공한 경로는 항상 유효
    user_paths = set(tuple(p) for p in USER_PROVIDED_CATEGORIES)
    
    # 유효한 경로만 필터링
    valid_categories = []
    for path in all_categories:
        path_tuple = tuple(path)
        # 사용자가 제공한 경로이거나 유효성 검사를 통과한 경로
        if path_tuple in user_paths or is_valid_category_path(path):
            valid_categories.append(path)
    
    # 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_categories, f, ensure_ascii=False, indent=2)
    
    print(f"원본: {len(all_categories)}개")
    print(f"필터링 후: {len(valid_categories)}개")
    print(f"제거: {len(all_categories) - len(valid_categories)}개")
    print(f"\n필터링된 파일 저장: {output_file}")
    
    return valid_categories

if __name__ == "__main__":
    filter_categories(
        "data/ssadagu/all_categories_final.json",
        "data/ssadagu/all_categories_valid.json"
    )



