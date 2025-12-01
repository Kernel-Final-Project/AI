"""
제목 생성 모듈 테스트
"""
from content_ai.title_generator import generate_title, generate_titles, select_best_title

def test_title_generation():
    """제목 생성 테스트"""
    print("=" * 50)
    print("제목 생성 모듈 테스트")
    print("=" * 50)
    
    # 테스트 데이터
    keyword = "요가매트"
    product_info = "싸다구 프리미엄 요가매트, 두께 10mm, 미끄럼 방지"
    
    print(f"\n[테스트 데이터]")
    print(f"키워드: {keyword}")
    print(f"상품 정보: {product_info}")
    
    # 1. 제목 리스트 생성 테스트
    print(f"\n[1] 제목 리스트 생성")
    titles = generate_titles(keyword, product_info)
    
    if titles:
        print(f"✅ {len(titles)}개 제목 생성 성공")
        print("\n생성된 제목들:")
        for i, title in enumerate(titles, 1):
            print(f"  {i}. {title} ({len(title)}자)")
    else:
        print("❌ 제목 생성 실패")
        return False
    
    # 2. 최적 제목 선택 테스트
    print(f"\n[2] 최적 제목 선택")
    best_title = select_best_title(titles, keyword)
    
    if best_title:
        print(f"✅ 최적 제목 선택 성공")
        print(f"   선택된 제목: {best_title} ({len(best_title)}자)")
    else:
        print("❌ 최적 제목 선택 실패")
        return False
    
    # 3. 통합 함수 테스트
    print(f"\n[3] 통합 함수 테스트 (generate_title)")
    final_title = generate_title(keyword, product_info)
    
    if final_title:
        print(f"✅ 통합 함수 성공")
        print(f"   최종 제목: {final_title} ({len(final_title)}자)")
    else:
        print("❌ 통합 함수 실패")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 모든 테스트 통과!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_title_generation()

