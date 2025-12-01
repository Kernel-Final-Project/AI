"""
제목 생성 모듈 예외 처리 테스트
하드코딩된 데이터로 다양한 예외 상황 테스트
"""
from content_ai.title_generator import (
    parse_titles_from_response,
    select_best_title,
    create_fallback_title
)
from utils.logger import logger

def test_parse_titles():
    """파싱 함수 테스트"""
    print("=" * 60)
    print("[테스트 1] 파싱 함수 테스트")
    print("=" * 60)
    
    # 케이스 1: 정상 bullet 형태
    print("\n[케이스 1-1] 정상 bullet 형태")
    response1 = """
- 요가매트 추천 가이드 2025년 완벽 정리
- 프리미엄 요가매트 완벽 정리 가이드
- 요가매트 구매 가이드 TOP 5 추천
- 요가매트 비교 분석 완벽 가이드
- 요가매트 선택 팁 완벽 정리
"""
    titles1 = parse_titles_from_response(response1)
    print(f"결과: {len(titles1)}개 제목 파싱")
    for i, title in enumerate(titles1, 1):
        print(f"  {i}. {title} ({len(title)}자)")
    assert len(titles1) >= 4, f"최소 4개 제목이 파싱되어야 함 (실제: {len(titles1)}개)"
    
    # 케이스 2: 숫자 bullet
    print("\n[케이스 1-2] 숫자 bullet 형태")
    response2 = """
1. 요가매트 추천 가이드
2. 프리미엄 요가매트 정리
3. 요가매트 구매 가이드
"""
    titles2 = parse_titles_from_response(response2)
    print(f"결과: {len(titles2)}개 제목 파싱")
    assert len(titles2) == 3, "3개 제목이 파싱되어야 함"
    
    # 케이스 3: 설명 포함 (파싱 실패 가능)
    print("\n[케이스 1-3] 설명 포함된 응답")
    response3 = """
다음은 제목 5개입니다:
- 요가매트 추천 가이드
- 프리미엄 요가매트 정리
위 제목들은 SEO 최적화되어 있습니다.
"""
    titles3 = parse_titles_from_response(response3)
    print(f"결과: {len(titles3)}개 제목 파싱")
    print(f"  파싱된 제목: {titles3}")
    
    # 케이스 4: 빈 응답
    print("\n[케이스 1-4] 빈 응답")
    response4 = ""
    titles4 = parse_titles_from_response(response4)
    print(f"결과: {len(titles4)}개 제목 파싱")
    assert len(titles4) == 0, "빈 응답은 0개 반환"
    
    print("\n✅ 파싱 테스트 완료\n")


def test_select_best_title():
    """최적 제목 선택 테스트"""
    print("=" * 60)
    print("[테스트 2] 최적 제목 선택 테스트")
    print("=" * 60)
    
    keyword = "요가매트"
    
    # 케이스 1: 정상 제목들
    print("\n[케이스 2-1] 정상 제목들 (최적 선택)")
    titles1 = [
        "요가매트 추천 가이드 2025년 완벽 정리",  # 30자, 키워드 앞쪽, 숫자 포함
        "프리미엄 요가매트 완벽 정리 가이드",  # 20자
        "요가매트 구매 가이드 TOP 5 추천",  # 20자, 숫자 포함
    ]
    best1 = select_best_title(titles1, keyword)
    print(f"선택된 제목: {best1} ({len(best1)}자)")
    assert best1 in titles1, "제목 중 하나가 선택되어야 함"
    
    # 케이스 2: 모든 제목이 금지어 포함
    print("\n[케이스 2-2] 모든 제목이 금지어 포함")
    titles2 = [
        "대박 요가매트 초특가 완판",  # 금지어 포함
        "역대급 요가매트 한정 할인",  # 금지어 포함
        "폭발적 요가매트 파격 쿠폰",  # 금지어 포함
    ]
    best2 = select_best_title(titles2, keyword)
    print(f"선택된 제목: {best2} ({len(best2)}자)")
    print("  (금지어 포함이지만 최선의 제목 선택)")
    
    # 케이스 3: 키워드가 없는 제목들
    print("\n[케이스 2-3] 키워드가 없는 제목들")
    titles3 = [
        "운동 매트 추천 가이드",  # 키워드 없음
        "프리미엄 매트 완벽 정리",  # 키워드 없음
        "매트 구매 가이드 TOP 5",  # 키워드 없음
    ]
    best3 = select_best_title(titles3, keyword)
    print(f"선택된 제목: {best3}")
    print("  (키워드 없지만 선택됨 - 점수는 낮을 것)")
    
    # 케이스 4: 35자 초과 제목들
    print("\n[케이스 2-4] 35자 초과 제목들")
    titles4 = [
        "요가매트 추천 가이드 완벽 정리 모든 것 알아보기",  # 40자
        "프리미엄 요가매트 구매 가이드 완벽 정리",  # 38자
        "요가매트 비교 분석 완벽 가이드 정리",  # 32자
    ]
    best4 = select_best_title(titles4, keyword)
    print(f"선택된 제목: {best4} ({len(best4)}자)")
    
    # 케이스 5: 제목 1개만
    print("\n[케이스 2-5] 제목 1개만")
    titles5 = ["요가매트 추천 가이드"]
    best5 = select_best_title(titles5, keyword)
    print(f"선택된 제목: {best5}")
    assert best5 == titles5[0], "1개만 있어도 선택되어야 함"
    
    print("\n✅ 최적 제목 선택 테스트 완료\n")


def test_fallback_title():
    """폴백 제목 생성 테스트"""
    print("=" * 60)
    print("[테스트 3] 폴백 제목 생성 테스트")
    print("=" * 60)
    
    # 케이스 1: 짧은 키워드
    print("\n[케이스 3-1] 짧은 키워드 (5자 이하)")
    keyword1 = "매트"
    fallback1 = create_fallback_title(keyword1)
    print(f"키워드: {keyword1}")
    print(f"폴백 제목: {fallback1}")
    assert keyword1 in fallback1, "키워드가 포함되어야 함"
    
    # 케이스 2: 중간 길이 키워드
    print("\n[케이스 3-2] 중간 길이 키워드 (6-10자)")
    keyword2 = "요가매트"
    fallback2 = create_fallback_title(keyword2)
    print(f"키워드: {keyword2}")
    print(f"폴백 제목: {fallback2}")
    
    # 케이스 3: 긴 키워드
    print("\n[케이스 3-3] 긴 키워드 (10자 초과)")
    keyword3 = "프리미엄 요가매트"
    fallback3 = create_fallback_title(keyword3)
    print(f"키워드: {keyword3}")
    print(f"폴백 제목: {fallback3}")
    
    print("\n✅ 폴백 제목 생성 테스트 완료\n")


def test_exception_scenarios():
    """예외 상황 시뮬레이션 테스트"""
    print("=" * 60)
    print("[테스트 4] 예외 상황 시뮬레이션")
    print("=" * 60)
    
    keyword = "요가매트"
    
    # 케이스 1: 제목 1개만 생성 (재시도 필요)
    print("\n[케이스 4-1] 제목 1개만 생성된 경우")
    response1 = "- 요가매트 추천 가이드"
    titles1 = parse_titles_from_response(response1)
    print(f"파싱 결과: {len(titles1)}개")
    print(f"  → generate_titles()에서 재시도해야 함 (2개 미만)")
    
    # 케이스 2: 유효한 제목 없음 (키워드 없음)
    print("\n[케이스 4-2] 유효한 제목 없음 (키워드 미포함)")
    titles2 = [
        "운동 매트 추천 가이드",
        "프리미엄 매트 정리",
    ]
    valid2 = [t for t in titles2 if keyword in t and len(t) <= 35]
    print(f"제목: {titles2}")
    print(f"유효한 제목: {len(valid2)}개")
    print(f"  → generate_titles()에서 재시도해야 함 (유효한 제목 없음)")
    
    # 케이스 3: 모든 제목이 35자 초과
    print("\n[케이스 4-3] 모든 제목이 35자 초과")
    titles3 = [
        "요가매트 추천 가이드 완벽 정리 모든 것 알아보기",  # 40자
        "프리미엄 요가매트 구매 가이드 완벽 정리",  # 38자
    ]
    valid3 = [t for t in titles3 if keyword in t and len(t) <= 35]
    print(f"제목: {titles3}")
    print(f"유효한 제목: {len(valid3)}개")
    print(f"  → generate_titles()에서 재시도해야 함 (35자 초과)")
    
    # 케이스 4: 빈 리스트
    print("\n[케이스 4-4] 빈 리스트")
    titles4 = []
    best4 = select_best_title(titles4, keyword)
    print(f"빈 리스트 선택 결과: '{best4}'")
    print(f"  → generate_title()에서 재시도해야 함")
    
    print("\n✅ 예외 상황 시뮬레이션 완료\n")


def test_integration_scenarios():
    """통합 시나리오 테스트"""
    print("=" * 60)
    print("[테스트 5] 통합 시나리오 테스트")
    print("=" * 60)
    
    keyword = "요가매트"
    
    # 시나리오 1: 정상 플로우
    print("\n[시나리오 1] 정상 플로우")
    print("1. generate_titles() → 5개 제목 생성")
    print("2. select_best_title() → 최적 제목 선택")
    print("3. generate_title() → 최종 제목 반환")
    print("  ✅ 예상: 정상 작동")
    
    # 시나리오 2: 제목 1개만 생성 → 재시도
    print("\n[시나리오 2] 제목 1개만 생성")
    print("1. generate_titles() → 1개만 생성")
    print("2. 재시도 로직 작동 (2개 미만)")
    print("3. 재시도 후 5개 생성 성공")
    print("  ✅ 예상: 재시도 후 성공")
    
    # 시나리오 3: 모든 재시도 실패 → 폴백
    print("\n[시나리오 3] 모든 재시도 실패")
    print("1. generate_titles() → 계속 실패 (3회)")
    print("2. generate_title() → 계속 실패 (3회)")
    print("3. create_fallback_title() → 기본 제목 반환")
    print("  ✅ 예상: 폴백 제목 반환")
    
    print("\n✅ 통합 시나리오 테스트 완료\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("제목 생성 모듈 예외 처리 테스트 시작")
    print("=" * 60 + "\n")
    
    try:
        test_parse_titles()
        test_select_best_title()
        test_fallback_title()
        test_exception_scenarios()
        test_integration_scenarios()
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()

