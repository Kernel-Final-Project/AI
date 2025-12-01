"""
무신사 카테고리 구조 상세 분석
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from auto_posting.browser_utils import setup_browser
from parsers.musinsa.config import BASE_URL, MUSINSA_SELECTORS


def analyze_category_structure():
    """카테고리 구조 상세 분석"""
    driver = setup_browser(headless=False)
    
    try:
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 카테고리 메뉴 열기
        wait = WebDriverWait(driver, 5)
        category_icon = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, MUSINSA_SELECTORS["category_icon"]))
        )
        category_icon.click()
        time.sleep(1)
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        print("=" * 80)
        print("1. 모든 1단계 카테고리 (CategorySubHeader__ClickableTitle)")
        print("=" * 80)
        
        first_level_links = modal.find_elements(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
        print(f"총 {len(first_level_links)}개 발견\n")
        
        for i, link in enumerate(first_level_links, 1):
            text = link.text.strip()
            href = link.get_attribute('href')
            category_id = link.get_attribute('data-category-id')
            print(f"{i:3d}. {text}")
            print(f"     href: {href}")
            print(f"     data-category-id: {category_id}")
            print()
        
        print("=" * 80)
        print("2. CategorySubRow 컨테이너 분석")
        print("=" * 80)
        
        category_rows = modal.find_elements(By.CSS_SELECTOR, "div.CategorySubRow__StyledContainer-sc-gndfto-0")
        print(f"총 {len(category_rows)}개 발견\n")
        
        for i, row in enumerate(category_rows[:10], 1):  # 처음 10개만
            try:
                dep1_link = row.find_element(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
                dep1_name = dep1_link.text.strip()
                
                dep2_links = row.find_elements(By.CSS_SELECTOR, "a.CategorySubItem__StyledContainer-sc-1kgwyy5-0")
                dep2_count = len([l for l in dep2_links if l.text.strip() and l.text.strip() != "전체 보기"])
                
                print(f"{i}. {dep1_name}")
                print(f"   → 2단계 카테고리: {dep2_count}개")
                
                # 처음 5개 2단계만 출력
                for j, dep2_link in enumerate(dep2_links[:5], 1):
                    dep2_text = dep2_link.text.strip()
                    if dep2_text and dep2_text != "전체 보기":
                        print(f"      {j}. {dep2_text}")
                if dep2_count > 5:
                    print(f"      ... 외 {dep2_count - 5}개")
                print()
            except Exception as e:
                print(f"{i}. 오류: {e}\n")
        
        print("=" * 80)
        print("3. 모든 CategorySubRow 구조 분석 (처음 17개)")
        print("=" * 80)
        
        for i, row in enumerate(category_rows, 1):
            print(f"\n[{i}/{len(category_rows)}] CategorySubRow 분석:")
            
            # 모든 링크 찾기
            all_links_in_row = row.find_elements(By.TAG_NAME, "a")
            print(f"  총 링크 개수: {len(all_links_in_row)}")
            
            # CategorySubHeader__ClickableTitle 찾기
            try:
                header_link = row.find_element(By.CSS_SELECTOR, "a.CategorySubHeader__ClickableTitle-sc-e6cyf1-2")
                print(f"  ✓ 1단계 카테고리: '{header_link.text.strip()}'")
            except:
                print(f"  ✗ 1단계 카테고리 없음")
            
            # 다른 클래스의 링크들 확인
            for link in all_links_in_row[:5]:  # 처음 5개만
                text = link.text.strip()
                classes = link.get_attribute('class')
                if text:
                    print(f"    - '{text}' (클래스: {classes[:50]}...)")
            
            if len(all_links_in_row) > 5:
                print(f"    ... 외 {len(all_links_in_row) - 5}개")
        
        print("\n" + "=" * 80)
        print("4. 모달 전체 구조 - 다른 카테고리 헤더 찾기")
        print("=" * 80)
        
        # CategorySubHeader__ClickableTitle 외의 다른 헤더 클래스 찾기
        all_links = modal.find_elements(By.TAG_NAME, "a")
        
        # 모든 링크의 클래스 분석
        class_counts = {}
        for link in all_links:
            classes = link.get_attribute('class')
            if classes:
                # 클래스 이름에서 주요 부분 추출
                if 'CategorySubHeader' in classes:
                    class_counts['CategorySubHeader'] = class_counts.get('CategorySubHeader', 0) + 1
                elif 'CategorySubItem' in classes:
                    class_counts['CategorySubItem'] = class_counts.get('CategorySubItem', 0) + 1
                elif 'gtm-click-button' in classes:
                    class_counts['gtm-click-button'] = class_counts.get('gtm-click-button', 0) + 1
        
        print("클래스별 링크 개수:")
        for cls, count in class_counts.items():
            print(f"  {cls}: {count}개")
        
        # "상의", "아우터", "바지"를 메인 카테고리로 가진 링크 찾기
        print("\n'상의', '아우터', '바지'를 메인 카테고리로 가진 링크 찾기:")
        target_texts = ["상의", "아우터", "바지"]
        
        for target_text in target_texts:
            # CategorySubHeader 클래스를 가진 링크 중에서 찾기
            header_links = modal.find_elements(By.CSS_SELECTOR, "a[class*='CategorySubHeader']")
            target_header = [link for link in header_links if link.text.strip() == target_text]
            
            if target_header:
                print(f"\n'{target_text}' 메인 카테고리 발견!")
                for link in target_header:
                    print(f"  href: {link.get_attribute('href')}")
                    print(f"  클래스: {link.get_attribute('class')}")
            else:
                print(f"\n'{target_text}' 메인 카테고리 없음 (서브 카테고리만 존재)")
        
        # 모달의 다른 섹션 확인 (예: 왼쪽 메뉴, 오른쪽 메뉴 등)
        print("\n" + "=" * 80)
        print("5. 모달 내부 주요 div 구조 확인")
        print("=" * 80)
        
        # 모달 내부의 주요 div 컨테이너 찾기
        main_divs = modal.find_elements(By.CSS_SELECTOR, "div[class*='Category']")
        print(f"Category 관련 div: {len(main_divs)}개")
        
        # 클래스 이름으로 그룹화
        div_classes = {}
        for div in main_divs[:20]:  # 처음 20개만
            cls = div.get_attribute('class')
            if cls:
                key = cls.split()[0] if cls.split() else cls
                if key not in div_classes:
                    div_classes[key] = []
                div_classes[key].append(div)
        
        print("\n주요 div 클래스:")
        for cls, divs in list(div_classes.items())[:10]:
            print(f"  {cls}: {len(divs)}개")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    analyze_category_structure()

