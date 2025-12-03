"""
OpenAI 라이브러리 연결 테스트
"""
from openai import OpenAI
from utils.load_env import OPENAI_API_KEY

def test_connection():
    """기본 연결 테스트"""
    print("=" * 50)
    print("OpenAI 연결 테스트 시작")
    print("=" * 50)
    
    # 1. API 키 확인
    print(f"\n[1] API 키 확인")
    if not OPENAI_API_KEY:
        print("❌ API 키가 없습니다!")
        return False
    print(f"✅ API 키 있음 (길이: {len(OPENAI_API_KEY)})")
    print(f"   앞 10자: {OPENAI_API_KEY[:10]}...")
    
    # 2. 클라이언트 생성
    print(f"\n[2] OpenAI 클라이언트 생성")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ 클라이언트 생성 성공")
    except Exception as e:
        print(f"❌ 클라이언트 생성 실패: {e}")
        return False
    
    # 3. 간단한 API 호출 테스트
    print(f"\n[3] API 호출 테스트")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "안녕하세요. '테스트'라고만 답해주세요."}
            ],
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f"✅ API 호출 성공!")
        print(f"   응답: {result}")
        return True
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        print(f"   에러 타입: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_connection()
    print("\n" + "=" * 50)
    if success:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 테스트 실패 - 위의 에러를 확인하세요")
    print("=" * 50)

