"""
무신사 모달 구조 상세 분석 스크립트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

from auto_posting.browser_utils import setup_browser
from parsers.musinsa.config import BASE_URL, MUSINSA_SELECTORS


def analyze_modal_structure():
    """모달 구조 상세 분석"""
    driver = setup_browser(headless=False)
    
    try:
        # 메인 페이지 접속
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 카테고리 메뉴 열기
        wait = WebDriverWait(driver, 5)
        category_icon = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, MUSINSA_SELECTORS["category_icon"]))
        )
        category_icon.click()
        time.sleep(1)
        
        # 모달 찾기
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        print("=" * 80)
        print("1. 모달 기본 정보")
        print("=" * 80)
        print(f"모달 클래스: {modal.get_attribute('class')}")
        print(f"모달 HTML 길이: {len(modal.get_attribute('outerHTML'))}")
        
        # 모달 내부 구조 분석
        print("\n" + "=" * 80)
        print("2. 모달 내부 주요 컨테이너 찾기")
        print("=" * 80)
        
        # 주요 div 컨테이너 찾기
        containers = modal.find_elements(By.CSS_SELECTOR, "div")
        print(f"모달 내 div 개수: {len(containers)}")
        
        # ul, li 구조 확인
        ul_elements = modal.find_elements(By.TAG_NAME, "ul")
        print(f"모달 내 ul 개수: {len(ul_elements)}")
        
        li_elements = modal.find_elements(By.TAG_NAME, "li")
        print(f"모달 내 li 개수: {len(li_elements)}")
        
        # 모든 링크 찾기
        all_links = modal.find_elements(By.CSS_SELECTOR, "a[data-category-id]")
        print(f"모달 내 data-category-id 링크 개수: {len(all_links)}")
        
        print("\n" + "=" * 80)
        print("3. 처음 10개 링크 정보")
        print("=" * 80)
        for i, link in enumerate(all_links[:10], 1):
            print(f"{i}. 텍스트: '{link.text.strip()}'")
            print(f"   href: {link.get_attribute('href')}")
            print(f"   data-category-id: {link.get_attribute('data-category-id')}")
            print(f"   클래스: {link.get_attribute('class')}")
            # 부모 요소 확인
            try:
                parent = link.find_element(By.XPATH, "./..")
                print(f"   부모 태그: {parent.tag_name}, 클래스: {parent.get_attribute('class')}")
            except:
                pass
            print()
        
        # "뷰티" 링크 찾기
        print("=" * 80)
        print("4. '뷰티' 링크 분석")
        print("=" * 80)
        beauty_link = None
        for link in all_links:
            if "뷰티" in link.text.strip():
                beauty_link = link
                print(f"뷰티 링크 발견:")
                print(f"  텍스트: {link.text.strip()}")
                print(f"  href: {link.get_attribute('href')}")
                print(f"  data-category-id: {link.get_attribute('data-category-id')}")
                print(f"  클래스: {link.get_attribute('class')}")
                
                # 부모 요소들 확인
                try:
                    parent = link.find_element(By.XPATH, "./..")
                    print(f"  부모: {parent.tag_name}, 클래스: {parent.get_attribute('class')}")
                    grandparent = parent.find_element(By.XPATH, "./..")
                    print(f"  조부모: {grandparent.tag_name}, 클래스: {grandparent.get_attribute('class')}")
                except:
                    pass
                break
        
        if beauty_link:
            print("\n" + "=" * 80)
            print("5. '뷰티' hover 전후 비교")
            print("=" * 80)
            
            # hover 전 링크 개수
            before_links = modal.find_elements(By.CSS_SELECTOR, "a[data-category-id]")
            print(f"hover 전 링크 개수: {len(before_links)}")
            
            # hover
            ActionChains(driver).move_to_element(beauty_link).perform()
            time.sleep(1)
            
            # hover 후 링크 개수
            after_links = modal.find_elements(By.CSS_SELECTOR, "a[data-category-id]")
            print(f"hover 후 링크 개수: {len(after_links)}")
            
            # 새로 나타난 링크 찾기
            before_texts = {link.text.strip() for link in before_links}
            after_texts = {link.text.strip() for link in after_links}
            new_texts = after_texts - before_texts
            
            print(f"\n새로 나타난 카테고리: {len(new_texts)}개")
            for text in list(new_texts)[:10]:
                print(f"  - {text}")
            
            # 모달 내부 구조 다시 확인 (hover 후)
            print("\n" + "=" * 80)
            print("6. hover 후 모달 내부 구조 (일부 HTML)")
            print("=" * 80)
            modal_html = modal.get_attribute('outerHTML')
            print(modal_html[:3000])  # 처음 3000자만
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    analyze_modal_structure()


