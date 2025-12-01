"""
범용 HTML 크롤링 파이프라인 테스트 스크립트
"""
from parsers.base.ssr_csr_checker import check_ssr_csr
from parsers.base.html_extractor import extract_html, extract_html_with_fallback
from utils.logger import logger


def test_ssr_csr_check():
    """SSR/CSR 판별 테스트"""
    print("\n" + "="*60)
    print("SSR/CSR 판별 테스트")
    print("="*60)
    
    # 테스트할 URL들
    test_urls = [
        "https://www.musinsa.com",  # 무신사
        "https://ssadagu.kr",  # 싸다구
        "https://www.naver.com",  # 네이버 (SSR)
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            result = check_ssr_csr(url)
            print(f"  렌더링 타입: {result.rendering_type}")
            print(f"  신뢰도: {result.confidence:.2f}")
            print(f"  콘텐츠 포함: {result.has_content}")
            print(f"  스크립트 개수: {result.script_count}")
            print(f"  API 엔드포인트: {len(result.api_endpoints)}개")
            if result.api_endpoints:
                print(f"    - {result.api_endpoints[0]}")
            print(f"  JSON 데이터: {result.json_data}")
        except Exception as e:
            print(f"  ❌ 오류: {e}")


def test_html_extraction():
    """HTML 추출 테스트"""
    print("\n" + "="*60)
    print("HTML 추출 테스트")
    print("="*60)
    
    # 테스트할 URL들
    test_urls = [
        "https://www.musinsa.com",
        "https://ssadagu.kr",
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            # 자동 방법 선택
            print("  → 자동 방법으로 추출 중...")
            html = extract_html(url)
            print(f"  ✅ 성공: {len(html)} bytes")
            
            # HTML 일부 출력
            print(f"  HTML 미리보기 (처음 200자):")
            print(f"  {html[:200]}...")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")


def test_html_extraction_with_fallback():
    """Fallback 모드 HTML 추출 테스트"""
    print("\n" + "="*60)
    print("Fallback 모드 HTML 추출 테스트")
    print("="*60)
    
    test_urls = [
        "https://www.musinsa.com",
        "https://ssadagu.kr",
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            html = extract_html_with_fallback(url)
            print(f"  ✅ 성공: {len(html)} bytes")
        except Exception as e:
            print(f"  ❌ 오류: {e}")


def test_dom_elements_check():
    """DOM 요소 확인 기능 테스트"""
    print("\n" + "="*60)
    print("DOM 요소 확인 기능 테스트")
    print("="*60)
    
    from parsers.base.html_extractor import _extract_with_selenium
    
    test_urls = [
        "https://www.musinsa.com",  # 무신사 (CSR)
        "https://ssadagu.kr",  # 싸다구 (CSR)
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        try:
            print("  → Selenium으로 HTML 추출 중 (DOM 요소 확인 포함)...")
            html = _extract_with_selenium(url, wait_time=3)
            print(f"  ✅ 성공: {len(html)} bytes")
            
            # HTML에서 주요 요소 확인
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            found_elements = []
            if soup.find('body'):
                found_elements.append('body')
            if soup.find('article'):
                found_elements.append('article')
            if soup.find('main'):
                found_elements.append('main')
            if soup.select('.product') or soup.select('[class*="product"]'):
                found_elements.append('product 관련')
            if soup.find('h1') or soup.find('h2') or soup.find('h3'):
                found_elements.append('제목(h1-h3)')
            
            print(f"  발견된 주요 요소: {', '.join(found_elements) if found_elements else '없음'}")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 범용 HTML 크롤링 파이프라인 테스트 시작\n")
    
    # SSR/CSR 판별 테스트
    # test_ssr_csr_check()
    
    # HTML 추출 테스트 (자동 방법 선택)
    # test_html_extraction()
    
    # Fallback 모드 테스트
    # test_html_extraction_with_fallback()
    
    # DOM 요소 확인 기능 테스트
    test_dom_elements_check()
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")

