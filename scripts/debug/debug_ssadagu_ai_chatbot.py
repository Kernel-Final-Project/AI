"""
싸다구 AI 챗봇 동작 원인 분석 스크립트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json

from auto_posting.browser_utils import setup_browser


def analyze_ai_chatbot():
    """싸다구 사이트의 AI 챗봇 동작 분석"""
    url = "https://ssadagu.kr"
    
    print("="*60)
    print("싸다구 AI 챗봇 동작 원인 분석")
    print("="*60)
    
    driver = None
    try:
        # 브라우저 설정 (GUI 모드로 확인)
        print("\n[1단계] 브라우저 설정 중...")
        driver = setup_browser(headless=False)
        print("✅ 브라우저 설정 완료")
        
        # 페이지 로드
        print(f"\n[2단계] {url} 페이지 로드 중...")
        driver.get(url)
        time.sleep(5)  # 페이지 로드 대기
        
        print("\n[3단계] AI 챗봇 요소 분석 중...")
        
        # 1. AI 챗봇 관련 요소 찾기
        ai_selectors = [
            "//*[contains(@class, 'ai')]",
            "//*[contains(@class, 'AI')]",
            "//*[contains(@class, 'chatbot')]",
            "//*[contains(@class, 'Chatbot')]",
            "//*[contains(@id, 'ai')]",
            "//*[contains(@id, 'AI')]",
            "//*[contains(@id, 'chatbot')]",
            "//*[contains(@id, 'Chatbot')]",
        ]
        
        ai_elements = []
        for selector in ai_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    try:
                        tag_name = elem.tag_name
                        class_attr = elem.get_attribute("class") or ""
                        id_attr = elem.get_attribute("id") or ""
                        is_displayed = elem.is_displayed()
                        text = elem.text[:100] if elem.text else ""
                        
                        ai_elements.append({
                            "selector": selector,
                            "tag": tag_name,
                            "class": class_attr,
                            "id": id_attr,
                            "is_displayed": is_displayed,
                            "text": text
                        })
                    except:
                        continue
            except:
                continue
        
        print(f"\n  발견된 AI 관련 요소: {len(ai_elements)}개")
        for idx, elem_info in enumerate(ai_elements[:10], 1):  # 상위 10개만 출력
            print(f"\n  [{idx}]")
            print(f"    태그: {elem_info['tag']}")
            print(f"    Class: {elem_info['class']}")
            print(f"    ID: {elem_info['id']}")
            print(f"    표시됨: {elem_info['is_displayed']}")
            print(f"    텍스트: {elem_info['text'][:50]}...")
        
        # 2. JavaScript 이벤트 리스너 확인
        print("\n[4단계] JavaScript 이벤트 리스너 확인 중...")
        js_code = """
        var elements = document.querySelectorAll('*');
        var eventListeners = [];
        for (var i = 0; i < elements.length; i++) {
            var elem = elements[i];
            var classes = elem.className || '';
            var id = elem.id || '';
            if (classes.toLowerCase().includes('ai') || 
                classes.toLowerCase().includes('chatbot') ||
                id.toLowerCase().includes('ai') ||
                id.toLowerCase().includes('chatbot')) {
                eventListeners.push({
                    tag: elem.tagName,
                    class: classes,
                    id: id,
                    onclick: elem.onclick ? 'has onclick' : 'no onclick'
                });
            }
        }
        return eventListeners;
        """
        
        try:
            event_listeners = driver.execute_script(js_code)
            print(f"  발견된 이벤트 리스너: {len(event_listeners)}개")
            for idx, listener in enumerate(event_listeners[:5], 1):
                print(f"\n  [{idx}]")
                print(f"    태그: {listener.get('tag', 'N/A')}")
                print(f"    Class: {listener.get('class', 'N/A')}")
                print(f"    ID: {listener.get('id', 'N/A')}")
                print(f"    onclick: {listener.get('onclick', 'N/A')}")
        except Exception as e:
            print(f"  ⚠️  JavaScript 실행 오류: {e}")
        
        # 3. 페이지 소스에서 AI 챗봇 관련 스크립트 찾기
        print("\n[5단계] 페이지 소스에서 AI 챗봇 관련 스크립트 확인 중...")
        page_source = driver.page_source
        
        # AI 챗봇 관련 키워드 검색
        keywords = ['ai', 'chatbot', 'assistant', '챗봇', 'AI', 'Chatbot']
        found_scripts = []
        
        soup = BeautifulSoup(page_source, 'html.parser')
        scripts = soup.find_all('script')
        
        for script in scripts:
            script_text = script.string or ""
            for keyword in keywords:
                if keyword.lower() in script_text.lower():
                    # 키워드 주변 텍스트 추출
                    idx = script_text.lower().find(keyword.lower())
                    if idx != -1:
                        start = max(0, idx - 100)
                        end = min(len(script_text), idx + 200)
                        snippet = script_text[start:end]
                        found_scripts.append({
                            "keyword": keyword,
                            "snippet": snippet.replace('\n', ' ').strip()
                        })
                        break
        
        print(f"  발견된 관련 스크립트: {len(found_scripts)}개")
        for idx, script_info in enumerate(found_scripts[:5], 1):
            print(f"\n  [{idx}] 키워드: {script_info['keyword']}")
            print(f"    스니펫: {script_info['snippet'][:150]}...")
        
        # 4. LocalStorage/SessionStorage 확인
        print("\n[6단계] LocalStorage/SessionStorage 확인 중...")
        try:
            local_storage = driver.execute_script("return JSON.stringify(localStorage);")
            session_storage = driver.execute_script("return JSON.stringify(sessionStorage);")
            
            print("  LocalStorage:")
            if local_storage and local_storage != "{}":
                storage_data = json.loads(local_storage)
                for key, value in list(storage_data.items())[:5]:
                    print(f"    {key}: {str(value)[:50]}...")
            else:
                print("    (비어있음)")
            
            print("  SessionStorage:")
            if session_storage and session_storage != "{}":
                storage_data = json.loads(session_storage)
                for key, value in list(storage_data.items())[:5]:
                    print(f"    {key}: {str(value)[:50]}...")
            else:
                print("    (비어있음)")
        except Exception as e:
            print(f"  ⚠️  Storage 확인 오류: {e}")
        
        # 5. 닫기 버튼 찾기
        print("\n[7단계] AI 챗봇 닫기 버튼 찾기...")
        close_selectors = [
            "//*[contains(@class, 'ai')]//button[contains(@class, 'close')]",
            "//*[contains(@class, 'chatbot')]//button[contains(@class, 'close')]",
            "//*[contains(@class, 'ai')]//*[contains(text(), 'X')]",
            "//*[contains(@class, 'chatbot')]//*[contains(text(), 'X')]",
            "//*[contains(@class, 'ai')]//*[contains(text(), '×')]",
            "//*[contains(@class, 'chatbot')]//*[contains(text(), '×')]",
        ]
        
        close_buttons = []
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            close_buttons.append({
                                "selector": selector,
                                "tag": elem.tag_name,
                                "class": elem.get_attribute("class") or "",
                                "text": elem.text
                            })
                    except:
                        continue
            except:
                continue
        
        print(f"  발견된 닫기 버튼: {len(close_buttons)}개")
        for idx, btn in enumerate(close_buttons, 1):
            print(f"\n  [{idx}]")
            print(f"    선택자: {btn['selector']}")
            print(f"    태그: {btn['tag']}")
            print(f"    Class: {btn['class']}")
            print(f"    텍스트: {btn['text']}")
        
        # 6. 닫기 후 다시 열리는지 확인
        print("\n[8단계] 닫기 후 재등장 여부 확인...")
        if close_buttons:
            print("  닫기 버튼 클릭 시도...")
            try:
                first_close_btn = driver.find_element(By.XPATH, close_buttons[0]['selector'])
                first_close_btn.click()
                time.sleep(2)
                print("  ✅ 닫기 버튼 클릭 완료")
                
                # 다시 나타나는지 확인
                time.sleep(3)
                ai_elements_after = []
                for selector in ai_selectors[:3]:  # 처음 3개만 확인
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            try:
                                if elem.is_displayed():
                                    ai_elements_after.append({
                                        "selector": selector,
                                        "is_displayed": True
                                    })
                            except:
                                continue
                    except:
                        continue
                
                if ai_elements_after:
                    print(f"  ⚠️  닫은 후 다시 나타난 요소: {len(ai_elements_after)}개")
                    print("  → 자동으로 다시 열리는 것으로 보입니다")
                else:
                    print("  ✅ 닫은 후 재등장하지 않음")
            except Exception as e:
                print(f"  ⚠️  닫기 버튼 클릭 오류: {e}")
        else:
            print("  닫기 버튼을 찾지 못했습니다")
        
        # 7. 페이지 스크롤이나 상호작용 시 열리는지 확인
        print("\n[9단계] 상호작용 후 AI 챗봇 열림 여부 확인...")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        ai_elements_after_scroll = []
        for selector in ai_selectors[:3]:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            ai_elements_after_scroll.append(selector)
                            break
                    except:
                        continue
            except:
                continue
        
        if ai_elements_after_scroll:
            print(f"  ⚠️  스크롤 후 나타난 요소: {len(ai_elements_after_scroll)}개")
        else:
            print("  ✅ 스크롤 후 재등장하지 않음")
        
        print("\n" + "="*60)
        print("분석 완료")
        print("="*60)
        print("\n브라우저를 10초간 열어둡니다. 직접 확인해보세요...")
        time.sleep(10)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n브라우저 종료 중...")
            driver.quit()


if __name__ == "__main__":
    analyze_ai_chatbot()


