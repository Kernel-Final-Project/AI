"""
Implicit/Explicit Wait 구현 테스트
"""
from parsers.base.html_extractor import _extract_with_selenium
from utils.logger import logger


def test_implicit_explicit_wait():
    """Implicit/Explicit Wait 테스트"""
    print("\n" + "="*60)
    print("Implicit/Explicit Wait 구현 테스트")
    print("="*60)
    
    test_urls = [
        "https://www.musinsa.com",  # 무신사 (CSR)
        "https://ssadagu.kr",  # 싸다구 (CSR)
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            print("  → Selenium으로 HTML 추출 (Implicit/Explicit Wait 적용)...")
            html = _extract_with_selenium(
                url,
                implicit_wait_time=10,
                explicit_wait_timeout=10
            )
            
            print(f"  ✅ 성공!")
            print(f"  HTML 길이: {len(html)} bytes")
            
            # HTML에서 주요 요소 확인
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            body = soup.find('body')
            if body:
                print(f"  body 태그 존재: ✅")
                body_text = body.get_text(strip=True)
                print(f"  body 텍스트 길이: {len(body_text)}자")
            
            # 제목 확인
            title = soup.find('title')
            if title:
                print(f"  페이지 제목: {title.get_text(strip=True)[:50]}")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Implicit/Explicit Wait 테스트 시작\n")
    
    test_implicit_explicit_wait()
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")


