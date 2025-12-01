"""
싸다구 사이트의 모든 카테고리 경로 찾기
"""
from parsers.ssadagu.category_finder import find_all_category_paths, print_category_paths

if __name__ == "__main__":
    print("싸다구 사이트의 모든 카테고리 경로를 찾는 중...")
    print("이 작업은 시간이 걸릴 수 있습니다.\n")
    
    paths = find_all_category_paths()
    
    if paths:
        print_category_paths(paths)
        
        # JSON으로 저장 (선택사항)
        import json
        with open("data/ssadagu/all_categories.json", "w", encoding="utf-8") as f:
            json.dump(paths, f, ensure_ascii=False, indent=2)
        print("\n카테고리 경로가 data/ssadagu/all_categories.json에 저장되었습니다.")
    else:
        print("카테고리 경로를 찾을 수 없습니다.")



