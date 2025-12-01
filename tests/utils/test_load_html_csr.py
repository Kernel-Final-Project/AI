"""
load_html_csr() 함수 테스트
"""
from parsers.base.html_extractor import load_html_csr
from utils.logger import logger


def test_load_html_csr():
    """load_html_csr() 함수 테스트"""
    print("\n" + "="*60)
    print("load_html_csr() 함수 테스트")
    print("="*60)
    
    test_urls = [
        "https://www.musinsa.com",  # 무신사 (CSR)
        "https://ssadagu.kr",  # 싸다구 (CSR)
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            print("  → CSR 사이트 HTML 로드 및 파싱...")
            html, soup = load_html_csr(url, explicit_wait_timeout=10)
            
            print(f"  ✅ 성공!")
            print(f"  HTML 길이: {len(html)} bytes")
            print(f"  BeautifulSoup 객체 타입: {type(soup)}")
            
            # 파싱된 HTML에서 요소 확인
            title = soup.find('title')
            if title:
                print(f"  페이지 제목: {title.get_text(strip=True)[:50]}")
            
            body = soup.find('body')
            if body:
                body_text = body.get_text(strip=True)
                print(f"  body 텍스트 길이: {len(body_text)}자")
                print(f"  body 텍스트 미리보기: {body_text[:100]}...")
            
            # 링크 개수 확인
            links = soup.find_all('a')
            print(f"  링크 개수: {len(links)}개")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 load_html_csr() 테스트 시작\n")
    
    test_load_html_csr()
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")


