"""
BeautifulSoup 파싱 기능 테스트
"""
from parsers.base.html_extractor import load_html_ssr, _extract_with_requests
from utils.logger import logger


def test_bs4_parsing():
    """BeautifulSoup 파싱 테스트"""
    print("\n" + "="*60)
    print("BeautifulSoup 파싱 기능 테스트")
    print("="*60)
    
    test_urls = [
        "https://www.naver.com",  # 네이버 (SSR)
        "https://www.google.com",  # 구글 (SSR)
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            # load_html_ssr() 함수 테스트
            print("  → load_html_ssr() 함수로 HTML 로드 및 파싱...")
            html, soup = load_html_ssr(url, timeout=10)
            
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


def test_direct_extract():
    """직접 _extract_with_requests() 함수 테스트"""
    print("\n" + "="*60)
    print("직접 _extract_with_requests() 함수 테스트")
    print("="*60)
    
    url = "https://www.naver.com"
    print(f"\n[테스트] {url}")
    try:
        html, soup = _extract_with_requests(url, timeout=10)
        print(f"  ✅ 성공!")
        print(f"  HTML 길이: {len(html)} bytes")
        print(f"  BeautifulSoup 객체: {type(soup)}")
        print(f"  body 존재: {soup.find('body') is not None}")
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 BeautifulSoup 파싱 테스트 시작\n")
    
    # load_html_ssr() 함수 테스트
    test_bs4_parsing()
    
    # 직접 함수 테스트
    # test_direct_extract()
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")


