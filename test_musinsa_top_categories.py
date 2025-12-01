from selenium import webdriver
from selenium.webdriver.common.by import By
import time

from auto_posting.browser_utils import setup_browser
from musinsa_parser.category_crawler import build_top_categories
from utils.logger import logger


def test_musinsa_top_categories():
    print("=" * 70)
    print("무신사 1depth 상위 카테고리 테스트 시작")
    print("=" * 70)
    
    driver = None
    
    try:
        driver = setup_browser(headless=False)
        
        # ✅ 수정: 중복 URL 접속 제거 (build_top_categories 내부에서 처리)
        # BASE_URL 접속과 time.sleep(2) 제거
        
        # 2) 상위 카테고리 패널 열기
        print("[1] 상위 카테고리 패널 열기 및 추출 중...")
        
        # build_top_categories 내부에서 open_musinsa_category_panel을 호출하여
        # 자동으로 BASE_URL 접속 및 카테고리 패널 열기 수행
        top_categories = build_top_categories(driver)
        
        print("\n[2] 추출된 상위 카테고리 목록:")
        print("-" * 70)
        
        if not top_categories:
            print("❌ 상위 카테고리를 찾지 못했습니다.")
            return
        
        for idx, node in enumerate(top_categories, 1):
            print(f"[{idx}] {node.name}")
            print(f"   - url: {node.url}")
            print(f"   - xpath: {node.xpath}")
            print(f"   - category_id: {node.category_id}")
            print(f"   - node_type: {node.node_type}")
            print(f"   - depth: {node.depth}")
            print("")
        
        print(f"총 {len(top_categories)}개 카테고리 추출 완료.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


if __name__ == "__main__":
    test_musinsa_top_categories()

