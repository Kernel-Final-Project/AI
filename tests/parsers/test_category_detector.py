"""
카테고리 탐지 기능 테스트 스크립트
"""
from parsers.base.html_extractor import extract_html
from parsers.base.html_category_detector import (
    find_category_candidates, 
    filter_clickable_elements,
    detect_hover_needed
)
from parsers.base.category_interaction import (
    hover_element, 
    hover_and_wait_for_submenu,
    find_selenium_element,
    click_element
)
from parsers.base.category_clicker import click_category_with_fallback
from parsers.base.html_extractor import (
    handle_event_banner_and_navigate_to_main,
    detect_event_banner,
    is_main_page
)
from auto_posting.browser_utils import setup_browser
from utils.logger import logger
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def analyze_candidate(tag, index: int):
    """카테고리 후보를 분석하여 정보를 출력"""
    tag_name = tag.name.lower()
    classes = tag.get("class", [])
    element_id = tag.get("id", "")
    
    # 매칭된 패턴 확인
    matched_patterns = []
    from utils.category_patterns import (
        CATEGORY_TAGS,
        CATEGORY_CLASS_KEYWORDS,
        CATEGORY_ID_KEYWORDS
    )
    
    if tag_name in CATEGORY_TAGS:
        matched_patterns.append("tag")
    
    if classes:
        class_str = " ".join(classes).lower()
        if any(keyword in class_str for keyword in CATEGORY_CLASS_KEYWORDS):
            matched_patterns.append("class")
    
    if element_id:
        if any(keyword in element_id.lower() for keyword in CATEGORY_ID_KEYWORDS):
            matched_patterns.append("id")
    
    # 링크 정보 확인
    href = None
    if tag.name == 'a':
        href = tag.get('href', '')
    else:
        # 자식 요소 중 링크 찾기
        link = tag.find('a')
        if link:
            href = link.get('href', '')
    
    # 텍스트 내용 (일부만)
    text = tag.get_text(strip=True)[:50] if tag.get_text(strip=True) else ""
    
    print(f"  [{index}] <{tag_name}>")
    if classes:
        print(f"      class: {', '.join(classes[:3])}{'...' if len(classes) > 3 else ''}")
    if element_id:
        print(f"      id: {element_id}")
    print(f"      매칭 패턴: {', '.join(matched_patterns) if matched_patterns else '없음'}")
    if href:
        print(f"      링크: {href[:80]}{'...' if len(href) > 80 else ''}")
    if text:
        print(f"      텍스트: {text}...")
    print()


def test_category_detection():
    """카테고리 탐지 기능 테스트"""
    print("\n" + "="*60)
    print("카테고리 탐지 기능 테스트")
    print("="*60)
    
    # 테스트할 URL들
    test_urls = [
        "https://ssadagu.kr",  # 싸다구
        "https://www.musinsa.com",  # 무신사
    ]
    
    for url in test_urls:
        print(f"\n[테스트] {url}")
        print("-" * 60)
        
        try:
            # Step 1: 브라우저로 페이지 접속
            print("  → 브라우저로 페이지 접속 중...")
            driver = setup_browser(headless=True)
            driver.get(url)
            time.sleep(3)  # 페이지 로딩 대기
            
            # Step 2: 이벤트 배너 처리 및 메인 페이지로 이동
            print("  → 이벤트 배너 확인 및 처리 중...")
            success, final_url = handle_event_banner_and_navigate_to_main(driver, url)
            
            if success:
                print(f"  ✅ 메인 페이지로 이동 성공: {final_url}")
            else:
                print(f"  ⚠️  메인 페이지로 이동하지 못함 (현재: {final_url})")
                if detect_event_banner(driver):
                    print("  ⚠️  여전히 이벤트 페이지입니다. 이벤트 페이지에서 탐지 진행...")
            
            # Step 3: HTML 추출
            print("  → HTML 추출 중...")
            html = driver.page_source
            print(f"  ✅ HTML 추출 완료: {len(html):,} bytes")
            
            # 브라우저 종료
            driver.quit()
            
            # Step 4: 카테고리 후보 탐지
            print("  → 카테고리 후보 탐지 중...")
            candidates = find_category_candidates(html)
            print(f"  ✅ 발견된 후보: {len(candidates)}개")
            
            if not candidates:
                print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
                continue
            
            # Step 3: 결과 분석
            print(f"\n  [상위 10개 후보 분석]")
            print("-" * 60)
            
            # 상위 10개만 상세 분석
            top_candidates = candidates[:10]
            for idx, candidate in enumerate(top_candidates, 1):
                analyze_candidate(candidate, idx)
            
            # 링크가 있는 후보 필터링
            link_candidates = []
            for candidate in candidates:
                if candidate.name == 'a' and candidate.get('href'):
                    link_candidates.append(candidate)
                else:
                    link = candidate.find('a')
                    if link and link.get('href'):
                        link_candidates.append(candidate)
            
            print(f"  [요약]")
            print(f"    - 전체 후보: {len(candidates)}개")
            print(f"    - 링크 포함 후보: {len(link_candidates)}개")
            
            # 태그별 통계
            tag_stats = {}
            for candidate in candidates:
                tag_name = candidate.name
                tag_stats[tag_name] = tag_stats.get(tag_name, 0) + 1
            
            print(f"    - 태그별 분포:")
            for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      • <{tag}>: {count}개")
            
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


def test_musinsa_detailed():
    """무신사 카테고리 후보 상세 분석"""
    print("\n" + "="*60)
    print("무신사 카테고리 후보 상세 분석")
    print("="*60)
    
    url = "https://www.musinsa.com"
    
    try:
        # Step 1: 브라우저로 페이지 접속
        print("  → 브라우저로 페이지 접속 중...")
        driver = setup_browser(headless=True)
        driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기
        
        # 실제 접속된 URL 확인
        actual_url = driver.current_url
        print(f"  → 접속하려던 URL: {url}")
        print(f"  → 실제 접속된 URL: {actual_url}")
        
        # Step 2: 이벤트 배너 처리 및 메인 페이지로 이동
        print("  → 이벤트 배너 확인 및 처리 중...")
        success, final_url = handle_event_banner_and_navigate_to_main(driver, url)
        
        if success:
            print(f"  ✅ 메인 페이지로 이동 성공: {final_url}")
        else:
            print(f"  ⚠️  메인 페이지로 이동하지 못함 (현재: {final_url})")
            if detect_event_banner(driver):
                print("  ⚠️  여전히 이벤트 페이지입니다. 이벤트 페이지에서 탐지 진행...")
        
        # Step 3: HTML 추출
        print("  → HTML 추출 중...")
        html = driver.page_source
        driver.quit()
        print(f"  ✅ HTML 추출 완료: {len(html):,} bytes")
        
        # Step 2: 카테고리 후보 탐지
        print("  → 카테고리 후보 탐지 중...")
        candidates = find_category_candidates(html)
        print(f"  ✅ 발견된 후보: {len(candidates)}개")
        
        if not candidates:
            print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
            return
        
        # Step 3: 상위 30개 후보 상세 분석
        print(f"\n  [상위 30개 후보 상세 분석]")
        print("-" * 60)
        
        top_candidates = candidates[:30]
        for idx, candidate in enumerate(top_candidates, 1):
            analyze_candidate(candidate, idx)
        
        # 링크가 있는 후보만 필터링해서 출력
        print(f"\n  [링크 포함 후보 상세 분석]")
        print("-" * 60)
        
        link_candidates = []
        for candidate in candidates:
            href = None
            if candidate.name == 'a' and candidate.get('href'):
                href = candidate.get('href')
                link_candidates.append((candidate, href))
            else:
                link = candidate.find('a')
                if link and link.get('href'):
                    href = link.get('href')
                    link_candidates.append((candidate, href))
        
        print(f"  → 링크 포함 후보: {len(link_candidates)}개\n")
        
        # 링크 포함 후보 상위 20개 출력
        for idx, (candidate, href) in enumerate(link_candidates[:20], 1):
            tag_name = candidate.name
            classes = candidate.get("class", [])
            element_id = candidate.get("id", "")
            text = candidate.get_text(strip=True)[:60] if candidate.get_text(strip=True) else ""
            
            print(f"  [{idx}] <{tag_name}>")
            if classes:
                print(f"      class: {', '.join(classes[:3])}{'...' if len(classes) > 3 else ''}")
            if element_id:
                print(f"      id: {element_id}")
            print(f"      링크: {href[:100]}{'...' if len(href) > 100 else ''}")
            if text:
                print(f"      텍스트: {text}...")
            print()
        
        # 요약
        print(f"  [요약]")
        print(f"    - 전체 후보: {len(candidates)}개")
        print(f"    - 링크 포함 후보: {len(link_candidates)}개")
        
        # 태그별 통계
        tag_stats = {}
        for candidate in candidates:
            tag_name = candidate.name
            tag_stats[tag_name] = tag_stats.get(tag_name, 0) + 1
        
        print(f"    - 태그별 분포:")
        for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"      • <{tag}>: {count}개")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_empty_html():
    """빈 HTML 테스트"""
    print("\n" + "="*60)
    print("빈 HTML 테스트")
    print("="*60)
    
    try:
        candidates = find_category_candidates("<html><body></body></html>")
        print(f"  ✅ 빈 HTML 처리 완료: {len(candidates)}개 후보")
    except Exception as e:
        print(f"  ❌ 오류: {e}")


def test_filter_clickable_elements():
    """클릭 가능한 요소 필터링 테스트"""
    print("\n" + "="*60)
    print("클릭 가능한 요소 필터링 테스트")
    print("="*60)
    
    # 테스트 HTML 생성 (다양한 케이스 포함)
    test_html = """
    <html>
    <body>
        <!-- 1. <a> 태그 직접 -->
        <a href="/category1">카테고리 1</a>
        
        <!-- 2. <li> 내부에 <a> 포함 -->
        <li class="menu-item">
            <a href="/category2">카테고리 2</a>
        </li>
        
        <!-- 3. onclick 속성 -->
        <div onclick="openCategory()" class="category-menu">카테고리 3</div>
        
        <!-- 4. role="button" -->
        <div role="button" class="nav-item">카테고리 4</div>
        
        <!-- 5. class에 "btn" 포함 -->
        <div class="btn-category menu-btn">카테고리 5</div>
        
        <!-- 6. cursor:pointer 스타일 -->
        <div style="cursor:pointer; color: red;">카테고리 6</div>
        
        <!-- 7. cursor: pointer (공백 포함) -->
        <div style="cursor: pointer; padding: 10px;">카테고리 7</div>
        
        <!-- 8. 클릭 불가능한 요소 (일반 div) -->
        <div class="category-menu">일반 텍스트</div>
        
        <!-- 9. 중복 요소 (같은 태그) -->
        <li class="menu-item">
            <a href="/category9">카테고리 9</a>
        </li>
        
        <!-- 10. ul 내부에 li들 -->
        <ul class="category-list">
            <li><a href="/sub1">서브 1</a></li>
            <li><a href="/sub2">서브 2</a></li>
        </ul>
    </body>
    </html>
    """
    
    try:
        print("  → 테스트 HTML 파싱 중...")
        soup = BeautifulSoup(test_html, "html.parser")
        
        # 모든 요소를 후보로 만들기 (실제로는 find_category_candidates를 사용하지만 테스트용)
        all_elements = soup.find_all(True)
        print(f"  ✅ 전체 요소: {len(all_elements)}개")
        
        # 클릭 가능한 요소 필터링
        print("  → 클릭 가능한 요소 필터링 중...")
        clickable = filter_clickable_elements(all_elements)
        print(f"  ✅ 필터링된 클릭 가능한 요소: {len(clickable)}개")
        
        print("\n  [필터링 결과 상세]")
        print("-" * 60)
        for idx, elem in enumerate(clickable, 1):
            tag_name = elem.name
            classes = elem.get("class", [])
            href = elem.get("href", "")
            onclick = elem.get("onclick", "")
            role = elem.get("role", "")
            style = elem.get("style", "")
            text = elem.get_text(strip=True)[:30]
            
            # 클릭 가능한 이유 판단
            reasons = []
            if tag_name == "a":
                reasons.append("a 태그")
            if elem.find("a"):
                reasons.append("내부에 <a> 포함")
            if onclick:
                reasons.append("onclick 속성")
            if role == "button":
                reasons.append("role='button'")
            if classes and any("btn" in str(c).lower() for c in classes):
                reasons.append("class에 'btn' 포함")
            if style and ("cursor:pointer" in style.lower() or "cursor: pointer" in style.lower()):
                reasons.append("cursor:pointer 스타일")
            
            print(f"  [{idx}] <{tag_name}>")
            if classes:
                print(f"      class: {', '.join(classes)}")
            if href:
                print(f"      href: {href}")
            if onclick:
                print(f"      onclick: {onclick[:50]}")
            if role:
                print(f"      role: {role}")
            if style:
                print(f"      style: {style[:50]}")
            print(f"      이유: {', '.join(reasons) if reasons else '알 수 없음'}")
            print(f"      텍스트: {text}...")
            print()
        
        # 통계
        print("  [통계]")
        print(f"    - 전체 요소: {len(all_elements)}개")
        print(f"    - 클릭 가능한 요소: {len(clickable)}개")
        print(f"    - 필터링률: {len(clickable)/len(all_elements)*100:.1f}%")
        
        # 중복 제거 테스트
        print("\n  [중복 제거 테스트]")
        # 같은 요소를 두 번 추가
        duplicate_test = all_elements + all_elements[:5]  # 처음 5개를 중복 추가
        filtered_duplicate = filter_clickable_elements(duplicate_test)
        print(f"    - 중복 포함 리스트: {len(duplicate_test)}개")
        print(f"    - 필터링 후: {len(filtered_duplicate)}개")
        print(f"    - 중복 제거 확인: {'✅ 성공' if len(filtered_duplicate) <= len(clickable) else '❌ 실패'}")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_filter_with_real_html():
    """실제 HTML에서 클릭 가능한 요소 필터링 테스트"""
    print("\n" + "="*60)
    print("실제 HTML 클릭 가능한 요소 필터링 테스트")
    print("="*60)
    
    test_url = "https://ssadagu.kr"
    
    try:
        print(f"  → {test_url} HTML 로드 중...")
        html = extract_html(test_url, timeout=10)
        print(f"  ✅ HTML 로드 완료: {len(html):,} bytes")
        
        # 카테고리 후보 찾기
        print("  → 카테고리 후보 탐지 중...")
        candidates = find_category_candidates(html)
        print(f"  ✅ 발견된 후보: {len(candidates)}개")
        
        if not candidates:
            print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
            return
        
        # 클릭 가능한 요소 필터링
        print("  → 클릭 가능한 요소 필터링 중...")
        clickable = filter_clickable_elements(candidates)
        print(f"  ✅ 필터링된 클릭 가능한 요소: {len(clickable)}개")
        
        print("\n  [필터링 결과 요약]")
        print("-" * 60)
        print(f"    - 전체 후보: {len(candidates)}개")
        print(f"    - 클릭 가능한 요소: {len(clickable)}개")
        print(f"    - 필터링률: {len(clickable)/len(candidates)*100:.1f}%")
        
        # 상위 5개 상세 분석
        print("\n  [상위 5개 클릭 가능한 요소]")
        print("-" * 60)
        for idx, elem in enumerate(clickable[:5], 1):
            tag_name = elem.name
            classes = elem.get("class", [])
            href = None
            if tag_name == "a":
                href = elem.get("href", "")
            else:
                link = elem.find("a")
                if link:
                    href = link.get("href", "")
            
            text = elem.get_text(strip=True)[:40]
            
            print(f"  [{idx}] <{tag_name}>")
            if classes:
                print(f"      class: {', '.join(classes[:3])}{'...' if len(classes) > 3 else ''}")
            if href:
                print(f"      href: {href[:60]}{'...' if len(href) > 60 else ''}")
            if text:
                print(f"      텍스트: {text}...")
            print()
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_category_extraction_detailed():
    """카테고리 링크와 텍스트 상세 추출 테스트"""
    print("\n" + "="*60)
    print("카테고리 링크/텍스트 상세 추출 테스트")
    print("="*60)
    
    test_url = "https://ssadagu.kr"
    
    try:
        print(f"  → {test_url} HTML 로드 중...")
        html = extract_html(test_url, timeout=10)
        print(f"  ✅ HTML 로드 완료: {len(html):,} bytes")
        
        # 카테고리 후보 찾기
        print("  → 카테고리 후보 탐지 중...")
        candidates = find_category_candidates(html)
        print(f"  ✅ 발견된 후보: {len(candidates)}개")
        
        if not candidates:
            print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
            return
        
        # 클릭 가능한 요소 필터링
        print("  → 클릭 가능한 요소 필터링 중...")
        clickable = filter_clickable_elements(candidates)
        print(f"  ✅ 필터링된 클릭 가능한 요소: {len(clickable)}개")
        
        # 실제 카테고리 링크와 텍스트 추출
        print("\n  → 카테고리 링크/텍스트 추출 중...")
        category_items = []
        
        for elem in clickable:
            href = None
            text = None
            
            # <a> 태그 직접인 경우
            if elem.name == "a":
                href = elem.get("href", "")
                text = elem.get_text(strip=True)
            # 내부에 <a> 포함된 경우
            elif elem.find("a"):
                link = elem.find("a")
                href = link.get("href", "") if link else None
                # 텍스트는 링크의 텍스트를 우선, 없으면 부모 요소의 텍스트
                if link:
                    text = link.get_text(strip=True)
                    if not text:
                        text = elem.get_text(strip=True)
                else:
                    text = elem.get_text(strip=True)
            # onclick이나 다른 방식인 경우
            else:
                text = elem.get_text(strip=True)
                # onclick에서 URL 추출 시도
                onclick = elem.get("onclick", "")
                if onclick and ("href" in onclick or "url" in onclick.lower()):
                    # 간단한 URL 추출 시도 (실제로는 더 복잡할 수 있음)
                    import re
                    url_match = re.search(r'["\']([^"\']+)["\']', onclick)
                    if url_match:
                        href = url_match.group(1)
            
            # 유효한 카테고리 항목인지 확인
            if href or (text and len(text) > 0 and len(text) < 100):
                # 중복 제거 (같은 href나 텍스트)
                is_duplicate = False
                for existing in category_items:
                    if href and existing.get("href") == href:
                        is_duplicate = True
                        break
                    if text and existing.get("text") == text:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    category_items.append({
                        "href": href,
                        "text": text,
                        "tag": elem.name,
                        "classes": elem.get("class", [])
                    })
        
        print(f"  ✅ 추출된 카테고리 항목: {len(category_items)}개")
        
        # 링크가 있는 항목과 없는 항목 분리
        with_links = [item for item in category_items if item.get("href")]
        without_links = [item for item in category_items if not item.get("href")]
        
        print("\n  [카테고리 추출 결과 요약]")
        print("-" * 60)
        print(f"    - 전체 카테고리 항목: {len(category_items)}개")
        print(f"    - 링크 포함 항목: {len(with_links)}개")
        print(f"    - 링크 없음 (텍스트만): {len(without_links)}개")
        
        # 링크가 있는 카테고리 표시 (더 많이)
        print(f"\n  [링크가 있는 카테고리 (전체 {len(with_links)}개 중 상위 50개)]")
        print("-" * 60)
        for idx, item in enumerate(with_links[:50], 1):
            href = item.get("href", "")
            text = item.get("text", "")
            classes = item.get("classes", [])
            
            # href 정규화 (상대 경로를 절대 경로로)
            if href and not href.startswith("http"):
                if href.startswith("/"):
                    href = f"{test_url}{href}"
                elif href.startswith("./") or href.startswith("../"):
                    href = f"{test_url}/{href}"
            
            print(f"  [{idx}] {text[:60] if text else '(텍스트 없음)'}")
            print(f"      링크: {href}")
            if classes:
                print(f"      class: {', '.join(classes)}")
            print()
        
        # 다단계 카테고리 분석 (URL 파라미터 분석)
        print("\n  [다단계 카테고리 분석]")
        print("-" * 60)
        multi_level_categories = []
        for item in with_links:
            href = item.get("href", "")
            text = item.get("text", "")
            if href and "ss_tx=" in href:
                # URL 파라미터에서 카테고리 추출
                import urllib.parse
                parsed = urllib.parse.urlparse(href)
                params = urllib.parse.parse_qs(parsed.query)
                if "ss_tx" in params:
                    category_text = params["ss_tx"][0]
                    multi_level_categories.append({
                        "text": text,
                        "category_path": category_text,
                        "href": href
                    })
        
        if multi_level_categories:
            print(f"    발견된 다단계 카테고리: {len(multi_level_categories)}개")
            print("\n    [다단계 카테고리 예시 (상위 20개)]")
            for idx, cat in enumerate(multi_level_categories[:20], 1):
                print(f"    [{idx}] {cat['text']}")
                print(f"        경로: {cat['category_path']}")
                print(f"        링크: {cat['href'][:100]}{'...' if len(cat['href']) > 100 else ''}")
                print()
        else:
            print("    ⚠️  다단계 카테고리를 찾지 못했습니다.")
        
        # 카테고리 그룹화 분석
        print("\n  [카테고리 그룹화 분석]")
        print("-" * 60)
        category_groups = {
            "남성": [],
            "여성": [],
            "아동": [],
            "신발": [],
            "가방": [],
            "액세서리": [],
            "뷰티": [],
            "기타": []
        }
        
        for item in with_links:
            text = item.get("text", "").lower()
            href = item.get("href", "")
            categorized = False
            
            for group_name in ["남성", "여성", "아동", "신발", "가방", "액세서리", "뷰티"]:
                if group_name in text or (href and group_name in href.lower()):
                    category_groups[group_name].append(item)
                    categorized = True
                    break
            
            if not categorized:
                category_groups["기타"].append(item)
        
        for group_name, items in category_groups.items():
            if items:
                print(f"\n    [{group_name}] 카테고리: {len(items)}개")
                for idx, item in enumerate(items[:5], 1):  # 각 그룹당 상위 5개만
                    text = item.get("text", "")
                    href = item.get("href", "")
                    print(f"      {idx}. {text[:50]}")
                    print(f"         {href[:80]}{'...' if len(href) > 80 else ''}")
        
        # 통계 정보
        print("\n  [상세 통계]")
        print("-" * 60)
        print(f"    - 전체 카테고리 항목: {len(category_items)}개")
        print(f"    - 링크 포함: {len(with_links)}개 ({len(with_links)/len(category_items)*100:.1f}%)")
        print(f"    - 링크 없음: {len(without_links)}개 ({len(without_links)/len(category_items)*100:.1f}%)")
        print(f"    - 다단계 카테고리: {len(multi_level_categories)}개")
        
        # 태그별 통계
        tag_stats = {}
        for item in category_items:
            tag = item.get("tag", "unknown")
            tag_stats[tag] = tag_stats.get(tag, 0) + 1
        
        print(f"\n    [태그별 분포]")
        for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      • <{tag}>: {count}개 ({count/len(category_items)*100:.1f}%)")
        
        # 텍스트만 있는 상위 10개 표시
        if without_links:
            print("\n  [텍스트만 있는 카테고리 (상위 10개)]")
            print("-" * 60)
            for idx, item in enumerate(without_links[:10], 1):
                text = item.get("text", "")
                classes = item.get("classes", [])
                print(f"  [{idx}] {text[:60]}{'...' if len(text) > 60 else ''}")
                if classes:
                    print(f"      class: {', '.join(classes[:2])}{'...' if len(classes) > 2 else ''}")
                print()
        
        # 카테고리 텍스트 키워드 분석
        print("\n  [카테고리 텍스트 키워드 분석]")
        print("-" * 60)
        category_keywords = [
            "패션", "의류", "남성", "여성", "아동", "신발", "가방", "액세서리",
            "전자제품", "가전", "스마트폰", "컴퓨터", "생활용품", "식품", "뷰티",
            "홈", "인기", "신상", "할인", "세일", "베스트", "랭킹"
        ]
        
        found_keywords = {}
        for item in category_items:
            text = item.get("text", "").lower()
            for keyword in category_keywords:
                if keyword in text:
                    found_keywords[keyword] = found_keywords.get(keyword, 0) + 1
        
        if found_keywords:
            print("    발견된 키워드:")
            for keyword, count in sorted(found_keywords.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      • {keyword}: {count}회")
        else:
            print("    ⚠️  일반적인 카테고리 키워드를 찾지 못했습니다.")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_hover_detection():
    """hover 필요 요소 감지 테스트"""
    print("\n" + "="*60)
    print("Hover 필요 요소 감지 테스트")
    print("="*60)
    
    # 테스트 HTML 생성 (다양한 hover 패턴 포함)
    test_html = """
    <html>
    <body>
        <!-- 1. class에 hover 키워드 포함 -->
        <li class="menu-item has-submenu">
            <a href="/category1">카테고리 1</a>
            <ul class="submenu" style="display:none">
                <li><a href="/sub1">서브 1</a></li>
                <li><a href="/sub2">서브 2</a></li>
            </ul>
        </li>
        
        <!-- 2. dropdown 클래스 -->
        <div class="dropdown-menu">
            <a href="/item1">아이템 1</a>
        </div>
        
        <!-- 3. aria-haspopup 속성 -->
        <li aria-haspopup="true">
            <a href="/category2">카테고리 2</a>
        </li>
        
        <!-- 4. aria-expanded 속성 -->
        <div aria-expanded="false" class="nav-item">
            <a href="/category3">카테고리 3</a>
            <ul style="visibility:hidden">
                <li><a href="/sub3">서브 3</a></li>
            </ul>
        </div>
        
        <!-- 5. data-toggle="dropdown" -->
        <div data-toggle="dropdown" class="btn">
            <a href="/category4">카테고리 4</a>
        </div>
        
        <!-- 6. role="menu" -->
        <nav role="menu">
            <a href="/category5">카테고리 5</a>
        </nav>
        
        <!-- 7. hidden 클래스 + 메뉴 구조 -->
        <div class="hidden submenu-container">
            <ul>
                <li><a href="/sub4">서브 4</a></li>
                <li><a href="/sub5">서브 5</a></li>
            </ul>
        </div>
        
        <!-- 8. opacity:0 숨김 -->
        <div class="menu-wrapper">
            <ul style="opacity:0">
                <li><a href="/sub6">서브 6</a></li>
            </ul>
        </div>
        
        <!-- 9. onclick 없고 submenu 있음 -->
        <li class="nav-item">
            <a href="/category6">카테고리 6</a>
            <ul>
                <li><a href="/sub7">서브 7</a></li>
                <li><a href="/sub8">서브 8</a></li>
            </ul>
        </li>
        
        <!-- 10. 일반 메뉴 (hover 불필요) -->
        <li class="menu-item">
            <a href="/simple">단순 링크</a>
        </li>
        
        <!-- 11. onclick 있는 메뉴 (hover 불필요) -->
        <div onclick="openMenu()" class="menu-item">
            <a href="/click">클릭 메뉴</a>
        </div>
        
        <!-- 12. mega-menu -->
        <div class="mega-menu">
            <a href="/mega">메가 메뉴</a>
        </div>
        
        <!-- 13. has-children -->
        <li class="has-children">
            <a href="/parent">부모 메뉴</a>
        </li>
    </body>
    </html>
    """
    
    try:
        print("  → 테스트 HTML 파싱 중...")
        soup = BeautifulSoup(test_html, "html.parser")
        
        # 모든 요소 가져오기
        all_elements = soup.find_all(True)
        print(f"  ✅ 전체 요소: {len(all_elements)}개")
        
        # hover 필요 요소 감지
        print("  → Hover 필요 요소 감지 중...")
        hover_needed = []
        hover_not_needed = []
        
        for elem in all_elements:
            # body, html 제외
            if elem.name in ["html", "body"]:
                continue
            
            is_hover = detect_hover_needed(elem)
            if is_hover:
                hover_needed.append(elem)
            else:
                hover_not_needed.append(elem)
        
        print(f"  ✅ Hover 필요: {len(hover_needed)}개")
        print(f"  ✅ Hover 불필요: {len(hover_not_needed)}개")
        
        # 상세 분석
        print("\n  [Hover 필요 요소 상세 분석]")
        print("-" * 60)
        for idx, elem in enumerate(hover_needed, 1):
            tag_name = elem.name
            classes = elem.get("class", [])
            text = elem.get_text(strip=True)[:40]
            
            # 감지된 이유 분석
            reasons = []
            class_str = " ".join(classes).lower() if classes else ""
            
            hover_keywords = [
                "submenu", "sub-menu", "dropdown", "drop-menu",
                "has-submenu", "hover", "hover-open", "depth1", "depth2",
                "mega-menu", "flyout", "has-children", "parent"
            ]
            if any(kw in class_str for kw in hover_keywords):
                reasons.append("hover 키워드 클래스")
            
            if elem.get("aria-haspopup") == "true":
                reasons.append("aria-haspopup")
            
            if elem.get("aria-expanded") is not None:
                reasons.append("aria-expanded")
            
            if elem.get("data-toggle") == "dropdown" or elem.get("data-hover") == "true":
                reasons.append("data 속성")
            
            role = elem.get("role", "").lower()
            if role in ["menu", "menuitem"]:
                reasons.append("role 속성")
            
            # 숨겨진 요소 체크
            for child in elem.find_all(["ul", "div"], recursive=True, limit=3):
                style = child.get("style", "").replace(" ", "").lower()
                if any(p in style for p in ["display:none", "visibility:hidden", "opacity:0"]):
                    reasons.append("숨겨진 자식 요소")
                    break
            
            if not elem.get("onclick") and len(elem.find_all(["li", "a"], recursive=True, limit=5)) >= 2:
                reasons.append("onclick 없음 + 여러 메뉴 항목")
            
            print(f"  [{idx}] <{tag_name}>")
            if classes:
                print(f"      class: {', '.join(classes)}")
            if text:
                print(f"      텍스트: {text}...")
            print(f"      감지 이유: {', '.join(reasons) if reasons else '알 수 없음'}")
            print()
        
        # 통계
        print("  [통계]")
        print("-" * 60)
        print(f"    - 전체 요소: {len(all_elements) - 2}개 (html, body 제외)")
        print(f"    - Hover 필요: {len(hover_needed)}개 ({len(hover_needed)/(len(all_elements)-2)*100:.1f}%)")
        print(f"    - Hover 불필요: {len(hover_not_needed)}개 ({len(hover_not_needed)/(len(all_elements)-2)*100:.1f}%)")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_hover_detection_real_html():
    """실제 HTML에서 hover 필요 요소 감지 테스트"""
    print("\n" + "="*60)
    print("실제 HTML Hover 필요 요소 감지 테스트")
    print("="*60)
    
    test_url = "https://ssadagu.kr"
    
    try:
        print(f"  → {test_url} HTML 로드 중...")
        html = extract_html(test_url, timeout=10)
        print(f"  ✅ HTML 로드 완료: {len(html):,} bytes")
        
        # 카테고리 후보 찾기
        print("  → 카테고리 후보 탐지 중...")
        candidates = find_category_candidates(html)
        print(f"  ✅ 발견된 후보: {len(candidates)}개")
        
        if not candidates:
            print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
            return
        
        # 클릭 가능한 요소 필터링
        print("  → 클릭 가능한 요소 필터링 중...")
        clickable = filter_clickable_elements(candidates)
        print(f"  ✅ 필터링된 클릭 가능한 요소: {len(clickable)}개")
        
        # Hover 필요 요소 감지
        print("  → Hover 필요 요소 감지 중...")
        hover_needed = []
        hover_not_needed = []
        
        for elem in clickable:
            is_hover = detect_hover_needed(elem)
            if is_hover:
                hover_needed.append(elem)
            else:
                hover_not_needed.append(elem)
        
        print(f"  ✅ Hover 필요: {len(hover_needed)}개")
        print(f"  ✅ Hover 불필요: {len(hover_not_needed)}개")
        
        print("\n  [Hover 필요 요소 상세 분석 (상위 20개)]")
        print("-" * 60)
        for idx, elem in enumerate(hover_needed[:20], 1):
            tag_name = elem.name
            classes = elem.get("class", [])
            text = elem.get_text(strip=True)[:50]
            
            # 감지된 이유 분석
            reasons = []
            class_str = " ".join(classes).lower() if classes else ""
            
            hover_keywords = [
                "submenu", "sub-menu", "dropdown", "drop-menu",
                "has-submenu", "hover", "hover-open", "depth1", "depth2",
                "mega-menu", "flyout", "has-children", "parent"
            ]
            if any(kw in class_str for kw in hover_keywords):
                reasons.append("hover 키워드")
            
            if elem.get("aria-haspopup") == "true":
                reasons.append("aria-haspopup")
            
            if elem.get("aria-expanded") is not None:
                reasons.append("aria-expanded")
            
            if elem.get("data-toggle") == "dropdown":
                reasons.append("data-toggle")
            
            role = elem.get("role", "").lower()
            if role in ["menu", "menuitem"]:
                reasons.append("role")
            
            # 숨겨진 요소 체크
            hidden_found = False
            for child in elem.find_all(["ul", "div"], recursive=True, limit=3):
                style = child.get("style", "").replace(" ", "").lower()
                if any(p in style for p in ["display:none", "visibility:hidden", "opacity:0"]):
                    reasons.append("숨김 요소")
                    hidden_found = True
                    break
            
            if not hidden_found and not elem.get("onclick"):
                menu_items = elem.find_all(["li", "a"], recursive=True, limit=5)
                if len(menu_items) >= 2:
                    reasons.append("구조 분석")
            
            print(f"  [{idx}] <{tag_name}>")
            if classes:
                print(f"      class: {', '.join(classes[:3])}{'...' if len(classes) > 3 else ''}")
            if text:
                print(f"      텍스트: {text}...")
            print(f"      이유: {', '.join(reasons) if reasons else '알 수 없음'}")
            print()
        
        # 통계
        print("  [통계]")
        print("-" * 60)
        print(f"    - 전체 클릭 가능한 요소: {len(clickable)}개")
        print(f"    - Hover 필요: {len(hover_needed)}개 ({len(hover_needed)/len(clickable)*100:.1f}%)")
        print(f"    - Hover 불필요: {len(hover_not_needed)}개 ({len(hover_not_needed)/len(clickable)*100:.1f}%)")
        
        # 태그별 통계
        tag_stats_hover = {}
        tag_stats_no_hover = {}
        
        for elem in hover_needed:
            tag = elem.name
            tag_stats_hover[tag] = tag_stats_hover.get(tag, 0) + 1
        
        for elem in hover_not_needed:
            tag = elem.name
            tag_stats_no_hover[tag] = tag_stats_no_hover.get(tag, 0) + 1
        
        print(f"\n    [태그별 Hover 필요 분포]")
        for tag, count in sorted(tag_stats_hover.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      • <{tag}>: {count}개")
        
        print(f"\n    [태그별 Hover 불필요 분포]")
        for tag, count in sorted(tag_stats_no_hover.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      • <{tag}>: {count}개")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_hover_interaction():
    """hover 상호작용 테스트 (실제 Selenium 사용)"""
    print("\n" + "="*60)
    print("Hover 상호작용 테스트 (Selenium)")
    print("="*60)
    
    test_url = "https://ssadagu.kr"
    driver = None
    
    try:
        # 브라우저 설정
        print("  → 브라우저 설정 중...")
        driver = setup_browser(headless=False)  # GUI 모드로 테스트
        print("  ✅ 브라우저 설정 완료")
        
        # 페이지 로드
        print(f"  → {test_url} 페이지 로드 중...")
        driver.get(test_url)
        time.sleep(3)  # 페이지 로딩 대기
        print("  ✅ 페이지 로드 완료")
        
        # HTML 추출하여 hover 필요 요소 찾기
        print("  → HTML 추출 및 hover 필요 요소 탐지 중...")
        html = driver.page_source
        candidates = find_category_candidates(html)
        clickable = filter_clickable_elements(candidates)
        hover_needed = [elem for elem in clickable if detect_hover_needed(elem)]
        print(f"  ✅ hover 필요 요소: {len(hover_needed)}개 발견")
        
        if not hover_needed:
            print("  ⚠️  hover 필요 요소를 찾지 못했습니다.")
            return
        
        # 상위 5개 요소에 hover 테스트
        print(f"\n  → 상위 5개 요소에 hover 테스트 진행...")
        print("-" * 60)
        
        success_count = 0
        submenu_success_count = 0
        
        for idx, elem in enumerate(hover_needed[:10], 1):  # 상위 10개로 증가
            try:
                # BeautifulSoup Tag를 Selenium WebElement로 변환 (개선된 함수 사용)
                print(f"  [{idx}] 요소 찾기 중...")
                selenium_element = find_selenium_element(driver, elem)
                
                if not selenium_element:
                    tag_name = elem.name
                    text = elem.get_text(strip=True)[:40]
                    print(f"  [{idx}] <{tag_name}> - {text}...")
                    print(f"      ⚠️  Selenium 요소를 찾지 못했습니다")
                    continue
                
                tag_name = elem.name
                text = elem.get_text(strip=True)[:40]
                print(f"  [{idx}] <{tag_name}> - {text}...")
                
                # hover 테스트
                print(f"      → hover 수행 중...")
                hover_result = hover_element(driver, selenium_element, wait_seconds=0.5)
                
                if hover_result:
                    success_count += 1
                    print(f"      ✅ hover 성공")
                    
                    # submenu 대기 테스트
                    print(f"      → submenu 대기 중...")
                    submenu_result = hover_and_wait_for_submenu(
                        driver, selenium_element, timeout=2.0
                    )
                    
                    if submenu_result:
                        submenu_success_count += 1
                        print(f"      ✅ submenu 감지 성공")
                    else:
                        print(f"      ⚠️  submenu 감지 실패 (submenu가 없을 수도 있음)")
                else:
                    print(f"      ❌ hover 실패")
                
                # 다음 요소로 이동하기 전 대기
                time.sleep(1)
                print()
                
            except Exception as e:
                print(f"  [{idx}] ❌ 오류 발생: {e}")
                continue
        
        # 통계
        tested_count = min(10, len(hover_needed))
        print("  [테스트 결과 요약]")
        print("-" * 60)
        print(f"    - 테스트한 요소: {tested_count}개")
        if tested_count > 0:
            print(f"    - hover 성공: {success_count}개 ({success_count/tested_count*100:.1f}%)")
            print(f"    - submenu 감지 성공: {submenu_success_count}개 ({submenu_success_count/tested_count*100:.1f}%)")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n  → 브라우저 종료 중...")
            driver.quit()
            print("  ✅ 브라우저 종료 완료")


def test_click_interaction(test_url: str = "https://ssadagu.kr", site_name: str = None):
    """click 상호작용 테스트 (실제 Selenium 사용)"""
    if site_name is None:
        site_name = test_url.replace("https://", "").replace("http://", "").split("/")[0]
    
    print("\n" + "="*60)
    print(f"Click 상호작용 테스트 (Selenium) - {site_name}")
    print("="*60)
    driver = None
    
    try:
        # 브라우저 설정
        print("  → 브라우저 설정 중...")
        driver = setup_browser(headless=False)  # GUI 모드로 테스트
        print("  ✅ 브라우저 설정 완료")
        
        # 페이지 로드
        print(f"  → {test_url} 페이지 로드 중...")
        driver.get(test_url)
        time.sleep(3)  # 페이지 로딩 대기
        print("  ✅ 페이지 로드 완료")
        
        # HTML 추출하여 클릭 가능한 요소 찾기
        print("  → HTML 추출 및 클릭 가능한 요소 탐지 중...")
        html = driver.page_source
        candidates = find_category_candidates(html)
        clickable = filter_clickable_elements(candidates)
        print(f"  ✅ 클릭 가능한 요소: {len(clickable)}개 발견")
        
        if not clickable:
            print("  ⚠️  클릭 가능한 요소를 찾지 못했습니다.")
            return
        
        # hover가 필요하지 않은 클릭 가능한 요소 찾기 (직접 클릭 가능한 요소)
        non_hover_clickable = [elem for elem in clickable if not detect_hover_needed(elem)]
        print(f"  → hover 불필요한 클릭 가능한 요소: {len(non_hover_clickable)}개 발견")
        
        # hover가 필요한 요소도 테스트 (hover 후 클릭)
        hover_clickable = [elem for elem in clickable if detect_hover_needed(elem)]
        print(f"  → hover 필요한 클릭 가능한 요소: {len(hover_clickable)}개 발견")
        
        # 테스트할 요소 선택 (hover 불필요한 요소 우선, 없으면 hover 필요한 요소)
        test_elements = non_hover_clickable[:5] if non_hover_clickable else hover_clickable[:5]
        
        if not test_elements:
            print("  ⚠️  테스트할 요소를 찾지 못했습니다.")
            return
        
        print(f"\n  → 상위 {len(test_elements)}개 요소에 click 테스트 진행...")
        print("-" * 60)
        
        success_count = 0
        method_counts = {
            "normal_click": 0,
            "actionchains_click": 0,
            "js_click": 0
        }
        
        for idx, elem in enumerate(test_elements, 1):
            try:
                tag_name = elem.name
                text = elem.get_text(strip=True)[:40]
                print(f"  [{idx}] <{tag_name}> - {text}...")
                
                # hover가 필요한 요소인 경우 hover 먼저 수행
                if detect_hover_needed(elem):
                    print(f"      → hover 필요 요소 감지, hover 수행 중...")
                    selenium_element = find_selenium_element(driver, elem)
                    if selenium_element:
                        hover_result = hover_element(driver, selenium_element, wait_seconds=0.5)
                        if hover_result:
                            print(f"      ✅ hover 성공")
                            time.sleep(0.5)  # submenu 로딩 대기
                        else:
                            print(f"      ⚠️  hover 실패, 클릭 시도 계속 진행...")
                    else:
                        print(f"      ⚠️  Selenium 요소를 찾지 못했습니다")
                
                # 클릭 테스트
                print(f"      → click 수행 중...")
                success, method = click_element(driver, elem, wait_seconds=1.0)
                
                if success:
                    success_count += 1
                    method_counts[method] = method_counts.get(method, 0) + 1
                    print(f"      ✅ click 성공 (방법: {method})")
                    
                    # 페이지 변화 확인
                    time.sleep(1)
                    current_url = driver.current_url
                    print(f"      → 현재 URL: {current_url[:80]}...")
                else:
                    print(f"      ❌ click 실패: {method}")
                
                # 다음 요소로 이동하기 전 대기
                time.sleep(1)
                print()
                
            except Exception as e:
                print(f"  [{idx}] ❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 통계
        tested_count = len(test_elements)
        print("  [테스트 결과 요약]")
        print("-" * 60)
        print(f"    - 테스트한 요소: {tested_count}개")
        if tested_count > 0:
            print(f"    - click 성공: {success_count}개 ({success_count/tested_count*100:.1f}%)")
            print(f"    - 클릭 방법별 통계:")
            for method, count in method_counts.items():
                if count > 0:
                    print(f"      • {method}: {count}개")
        
    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n  → 브라우저 종료 중...")
            driver.quit()
            print("  ✅ 브라우저 종료 완료")


def test_event_banner_and_category_detection():
    """이벤트 배너 처리 후 카테고리 탐지 통합 테스트"""
    print("\n" + "="*60)
    print("이벤트 배너 처리 + 카테고리 탐지 통합 테스트")
    print("="*60)
    
    # 테스트할 URL들
    test_urls = [
        ("https://www.musinsa.com", "무신사"),
        ("https://ssadagu.kr", "싸다구"),
    ]
    
    for url, site_name in test_urls:
        print(f"\n[테스트] {site_name} ({url})")
        print("-" * 60)
        
        try:
            # Step 1: HTML 추출 (이벤트 배너 자동 처리 포함)
            print("  → HTML 추출 중 (이벤트 배너 자동 처리 포함)...")
            html = extract_html(url, timeout=10)
            print(f"  ✅ HTML 추출 완료: {len(html):,} bytes")
            
            # Step 2: 카테고리 후보 탐지
            print("  → 카테고리 후보 탐지 중...")
            candidates = find_category_candidates(html)
            print(f"  ✅ 발견된 후보: {len(candidates)}개")
            
            if not candidates:
                print("  ⚠️  카테고리 후보를 찾지 못했습니다.")
                continue
            
            # Step 3: 클릭 가능한 요소 필터링
            print("  → 클릭 가능한 요소 필터링 중...")
            clickable = filter_clickable_elements(candidates)
            print(f"  ✅ 클릭 가능한 요소: {len(clickable)}개")
            
            # Step 4: Hover 필요 요소 감지
            print("  → Hover 필요 요소 감지 중...")
            hover_needed = [elem for elem in clickable if detect_hover_needed(elem)]
            non_hover_clickable = [elem for elem in clickable if not detect_hover_needed(elem)]
            print(f"  ✅ Hover 필요 요소: {len(hover_needed)}개")
            print(f"  ✅ Hover 불필요 요소: {len(non_hover_clickable)}개")
            
            # Step 5: 상위 후보 분석
            print(f"\n  [상위 10개 카테고리 후보 분석]")
            print("-" * 60)
            
            top_candidates = candidates[:10]
            for idx, candidate in enumerate(top_candidates, 1):
                analyze_candidate(candidate, idx)
            
            # Step 6: 링크 포함 후보 분석
            link_candidates = []
            for candidate in candidates:
                if candidate.name == 'a' and candidate.get('href'):
                    link_candidates.append(candidate)
                else:
                    link = candidate.find('a')
                    if link and link.get('href'):
                        link_candidates.append(candidate)
            
            print(f"  [요약]")
            print(f"    - 전체 후보: {len(candidates)}개")
            print(f"    - 클릭 가능한 요소: {len(clickable)}개")
            print(f"    - Hover 필요 요소: {len(hover_needed)}개")
            print(f"    - Hover 불필요 요소: {len(non_hover_clickable)}개")
            print(f"    - 링크 포함 후보: {len(link_candidates)}개")
            
            # 태그별 통계
            tag_stats = {}
            for candidate in candidates:
                tag_name = candidate.name
                tag_stats[tag_name] = tag_stats.get(tag_name, 0) + 1
            
            print(f"    - 태그별 분포:")
            for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      • <{tag}>: {count}개")
            
            # 링크 예시 출력
            if link_candidates:
                print(f"\n  [링크 포함 카테고리 예시 (상위 5개)]")
                print("-" * 60)
                for idx, candidate in enumerate(link_candidates[:5], 1):
                    href = None
                    if candidate.name == 'a':
                        href = candidate.get('href')
                    else:
                        link = candidate.find('a')
                        if link:
                            href = link.get('href')
                    
                    text = candidate.get_text(strip=True)[:50] if candidate.get_text(strip=True) else ""
                    print(f"  [{idx}] {href[:80]}{'...' if href and len(href) > 80 else ''}")
                    if text:
                        print(f"      텍스트: {text}...")
                    print()
            
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


def test_category_click_with_fallback():
    """카테고리 클릭 및 submenu 감지 테스트"""
    print("\n" + "="*60)
    print("카테고리 클릭 + Submenu 감지 테스트")
    print("="*60)
    
    test_urls = [
        ("https://ssadagu.kr", "싸다구"),
    ]
    
    for url, site_name in test_urls:
        print(f"\n[테스트] {site_name} ({url})")
        print("-" * 60)
        
        driver = None
        try:
            # 브라우저 설정
            print("  → 브라우저 설정 중...")
            driver = setup_browser(headless=False)  # GUI 모드로 테스트
            print("  ✅ 브라우저 설정 완료")
            
            # 페이지 로드
            print(f"  → {url} 페이지 로드 중...")
            driver.get(url)
            time.sleep(3)
            
            # 이벤트 배너 처리
            print("  → 이벤트 배너 확인 및 처리 중...")
            from parsers.base.html_extractor import handle_event_banner_and_navigate_to_main
            success, final_url = handle_event_banner_and_navigate_to_main(driver, url)
            if success:
                print(f"  ✅ 메인 페이지로 이동 성공: {final_url}")
            else:
                print(f"  ⚠️  메인 페이지로 이동하지 못함 (현재: {final_url})")
            
            time.sleep(2)
            
            # 메인 페이지 URL 저장
            main_page_url = driver.current_url
            print(f"  📌 메인 페이지 URL 저장: {main_page_url}")
            
            # HTML 추출하여 카테고리 후보 찾기
            print("  → 카테고리 후보 탐지 중...")
            html = driver.page_source
            candidates = find_category_candidates(html)
            clickable = filter_clickable_elements(candidates)
            hover_needed = [elem for elem in clickable if detect_hover_needed(elem)]
            
            print(f"  ✅ 클릭 가능한 요소: {len(clickable)}개")
            print(f"  ✅ Hover 필요 요소: {len(hover_needed)}개")
            
            if not hover_needed:
                print("  ⚠️  Hover 필요 요소를 찾지 못했습니다.")
                # hover 불필요한 요소 중 상위 카테고리로 보이는 것 테스트
                non_hover = [elem for elem in clickable if not detect_hover_needed(elem)]
                test_elements = non_hover[:3]
                print(f"  → Hover 불필요한 요소 {len(test_elements)}개로 테스트 진행...")
            else:
                test_elements = hover_needed[:5]
                print(f"  → Hover 필요 요소 {len(test_elements)}개로 테스트 진행...")
            
            if not test_elements:
                print("  ⚠️  테스트할 요소를 찾지 못했습니다.")
                continue
            
            print(f"\n  [카테고리 클릭 테스트]")
            print("-" * 60)
            
            success_count = 0
            method_counts = {}
            
            for idx, elem in enumerate(test_elements, 1):
                try:
                    tag_name = elem.name
                    text = elem.get_text(strip=True)[:40] if elem.get_text(strip=True) else ""
                    print(f"  [{idx}] <{tag_name}> - {text}...")
                    
                    # BeautifulSoup Tag를 Selenium WebElement로 변환
                    selenium_element = find_selenium_element(driver, elem)
                    
                    if not selenium_element:
                        print(f"      ⚠️  Selenium 요소를 찾지 못했습니다")
                        continue
                    
                    # 메인 페이지로 돌아가기 (각 테스트 전)
                    if driver.current_url != main_page_url:
                        print(f"      → 메인 페이지로 복귀 중...")
                        driver.get(main_page_url)
                        time.sleep(2)
                    
                    # 카테고리 클릭 테스트
                    print(f"      → 카테고리 클릭 및 검증 중...")
                    success, method = click_category_with_fallback(
                        driver, 
                        selenium_element, 
                        timeout=2.0
                    )
                    
                    if success:
                        success_count += 1
                        method_counts[method] = method_counts.get(method, 0) + 1
                        print(f"      ✅ 성공 (방법: {method})")
                        
                        # URL 변경 확인
                        current_url = driver.current_url
                        if current_url != main_page_url:
                            print(f"      → URL 변경됨: {current_url[:80]}...")
                        else:
                            print(f"      → URL 변경 없음 (CSR 방식 또는 드롭다운 메뉴)")
                        
                        # 페이지 내용 확인
                        time.sleep(1)
                    else:
                        print(f"      ❌ 실패: {method}")
                    
                    # 다음 요소로 이동하기 전 대기
                    time.sleep(1)
                    print()
                    
                except Exception as e:
                    print(f"  [{idx}] ❌ 오류 발생: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # 통계
            tested_count = len(test_elements)
            print("  [테스트 결과 요약]")
            print("-" * 60)
            print(f"    - 테스트한 요소: {tested_count}개")
            if tested_count > 0:
                print(f"    - 성공: {success_count}개 ({success_count/tested_count*100:.1f}%)")
                print(f"    - 방법별 통계:")
                for method, count in method_counts.items():
                    if count > 0:
                        print(f"      • {method}: {count}개")
        
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                print("\n  → 브라우저 종료 중...")
                driver.quit()
                print("  ✅ 브라우저 종료 완료")


def test_category_tree_extraction():
    """카테고리 트리 추출 테스트"""
    print("\n" + "="*60)
    print("카테고리 트리 추출 테스트")
    print("="*60)
    
    test_urls = [
        ("https://ssadagu.kr", "싸다구"),
    ]
    
    for url, site_name in test_urls:
        print(f"\n[테스트] {site_name} ({url})")
        print("-" * 60)
        
        driver = None
        try:
            # 브라우저 설정
            print("  → 브라우저 설정 중...")
            driver = setup_browser(headless=False)
            print("  ✅ 브라우저 설정 완료")
            
            # 페이지 로드
            print(f"  → {url} 페이지 로드 중...")
            driver.get(url)
            time.sleep(3)
            
            # 이벤트 배너 처리
            print("  → 이벤트 배너 확인 및 처리 중...")
            from parsers.base.html_extractor import handle_event_banner_and_navigate_to_main
            success, final_url = handle_event_banner_and_navigate_to_main(driver, url)
            if success:
                print(f"  ✅ 메인 페이지로 이동 성공: {final_url}")
            else:
                print(f"  ⚠️  메인 페이지로 이동하지 못함 (현재: {final_url})")
            
            time.sleep(2)
            
            # SSR/CSR 판별
            print("  → SSR/CSR 판별 중...")
            from parsers.base.ssr_csr_checker import check_ssr_csr
            check_result = check_ssr_csr(url)
            print(f"  ✅ 렌더링 타입: {check_result.rendering_type} (신뢰도: {check_result.confidence:.2f})")
            
            # 카테고리 트리 추출
            print("  → 카테고리 트리 추출 중...")
            from parsers.base.category_tree_extractor import build_full_category_tree, build_category_tree_csr
            
            if check_result.rendering_type in ["CSR", "HYBRID"]:
                # CSR이면 Selenium 직접 사용
                print("  → CSR 방식: Selenium으로 직접 카테고리 탐지")
                tree = build_category_tree_csr(
                    driver=driver,
                    use_dynamic=True
                )
            else:
                # SSR이면 BeautifulSoup 사용
                print("  → SSR 방식: BeautifulSoup으로 카테고리 탐지")
                html = driver.page_source
                tree = build_full_category_tree(
                    html,
                    driver=driver,
                    use_dynamic=True
                )
            
            if tree:
                print(f"\n  ✅ 카테고리 트리 추출 성공 ({len(tree)}개 상위 카테고리)")
                print("\n  [카테고리 트리 구조 (전체)]")
                print("-" * 60)
                
                # 트리 출력 함수
                def print_tree(t: dict, indent: int = 0, max_items: int = 100):
                    prefix = "  " * indent
                    for idx, (text, children) in enumerate(list(t.items())[:max_items]):
                        is_leaf = len(children) == 0
                        leaf_mark = " [LEAF]" if is_leaf else f" [{len(children)}개 하위]"
                        print(f"{prefix}├─ {text}{leaf_mark}")
                        if children:
                            print_tree(children, indent + 1, max_items)
                
                print_tree(tree, indent=0, max_items=100)
                
                # 상세 정보 출력
                print("\n  [상세 정보]")
                print("-" * 60)
                
                def analyze_tree(t: dict, depth: int = 0) -> dict:
                    """트리 분석"""
                    total_nodes = len(t)
                    leaf_nodes = sum(1 for children in t.values() if len(children) == 0)
                    nodes_with_children = total_nodes - leaf_nodes
                    max_depth = depth
                    
                    for children in t.values():
                        if children:
                            sub_analysis = analyze_tree(children, depth + 1)
                            total_nodes += sub_analysis['total_nodes']
                            leaf_nodes += sub_analysis['leaf_nodes']
                            nodes_with_children += sub_analysis['nodes_with_children']
                            max_depth = max(max_depth, sub_analysis['max_depth'])
                    
                    return {
                        'total_nodes': total_nodes,
                        'leaf_nodes': leaf_nodes,
                        'nodes_with_children': nodes_with_children,
                        'max_depth': max_depth
                    }
                
                analysis = analyze_tree(tree)
                print(f"    - 총 카테고리 노드: {analysis['total_nodes']}개")
                print(f"    - 하위 카테고리 있는 노드: {analysis['nodes_with_children']}개")
                print(f"    - 리프 노드: {analysis['leaf_nodes']}개")
                print(f"    - 최대 깊이: {analysis['max_depth'] + 1}단계")
                
                # 상위 카테고리 목록 (상세)
                print("\n  [상위 카테고리 목록 (상세)]")
                print("-" * 60)
                for idx, (text, children) in enumerate(tree.items(), 1):
                    has_children = len(children) > 0
                    children_count = len(children) if has_children else 0
                    status = f"하위 {children_count}개" if has_children else "리프"
                    print(f"\n    [{idx:2d}] {text}")
                    print(f"        상태: {status}")
                    print(f"        텍스트 길이: {len(text)}자")
                    if has_children:
                        # 하위 카테고리도 표시 (최대 10개)
                        print(f"        하위 카테고리:")
                        for sub_idx, (sub_text, sub_children) in enumerate(list(children.items())[:10], 1):
                            sub_status = f"하위 {len(sub_children)}개" if len(sub_children) > 0 else "리프"
                            print(f"          {sub_idx:2d}. {sub_text} ({sub_status})")
                        if len(children) > 10:
                            print(f"          ... 외 {len(children) - 10}개")
                
                # 카테고리 텍스트 분석
                print("\n  [카테고리 텍스트 분석]")
                print("-" * 60)
                all_texts = list(tree.keys())
                if all_texts:
                    print(f"    - 총 {len(all_texts)}개 카테고리")
                    print(f"    - 평균 텍스트 길이: {sum(len(t) for t in all_texts) / len(all_texts):.1f}자")
                    print(f"    - 최소 텍스트 길이: {min(len(t) for t in all_texts)}자")
                    print(f"    - 최대 텍스트 길이: {max(len(t) for t in all_texts)}자")
                    
                    # 텍스트 길이별 분포
                    short_texts = [t for t in all_texts if len(t) <= 3]
                    medium_texts = [t for t in all_texts if 4 <= len(t) <= 10]
                    long_texts = [t for t in all_texts if len(t) > 10]
                    print(f"\n    텍스트 길이별 분포:")
                    print(f"      - 3자 이하: {len(short_texts)}개")
                    if short_texts:
                        print(f"        예시: {', '.join(short_texts[:10])}")
                    print(f"      - 4~10자: {len(medium_texts)}개")
                    if medium_texts:
                        print(f"        예시: {', '.join(medium_texts[:10])}")
                    print(f"      - 11자 이상: {len(long_texts)}개")
                    if long_texts:
                        print(f"        예시: {', '.join(long_texts[:10])}")
                
                # 전체 카테고리 목록
                print("\n  [전체 카테고리 목록]")
                print("-" * 60)
                for idx, text in enumerate(all_texts, 1):
                    print(f"    {idx:2d}. {text}")
                
            else:
                print("  ⚠️  카테고리 트리를 추출하지 못했습니다")
        
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                print("\n  → 브라우저 종료 중...")
                driver.quit()
                print("  ✅ 브라우저 종료 완료")


if __name__ == "__main__":
    print("\n🚀 카테고리 탐지 기능 테스트 시작\n")
    
    # 클릭 가능한 요소 필터링 테스트 (단위 테스트)
    # test_filter_clickable_elements()  # 주석 처리
    
    # 실제 HTML에서 클릭 가능한 요소 필터링 테스트
    # test_filter_with_real_html()  # 주석 처리
    
    # 카테고리 링크/텍스트 상세 추출 테스트
    # test_category_extraction_detailed()  # 주석 처리
    
    # Hover 필요 요소 감지 테스트 (단위 테스트)
    # test_hover_detection()  # 주석 처리
    
    # 실제 HTML에서 Hover 필요 요소 감지 테스트
    # test_hover_detection_real_html()  # 주석 처리
    
    # Hover 상호작용 테스트 (Selenium)
    # test_hover_interaction()  # 주석 처리
    
    # Click 상호작용 테스트 (Selenium) - ssadagu
    # test_click_interaction("https://ssadagu.kr", "ssadagu")
    
    # Click 상호작용 테스트 (Selenium) - 무신사
    # test_click_interaction("https://www.musinsa.com", "무신사")
    
    # 기본 카테고리 탐지 테스트 (무신사, ssadagu 둘 다 테스트)
    # test_category_detection()
    
    # 무신사 카테고리 후보 상세 분석
    # test_musinsa_detailed()
    
    # 이벤트 배너 처리 + 카테고리 탐지 통합 테스트
    # test_event_banner_and_category_detection()
    
    # 카테고리 클릭 + Submenu 감지 테스트
    # test_category_click_with_fallback()
    
    # 카테고리 트리 추출 테스트
    # test_category_tree_extraction()  # 주석 처리 (무거운 테스트)
    
    # 기본 카테고리 탐지 테스트 (무신사, ssadagu 둘 다 테스트)
    # test_category_detection()
    
    # Hover 상호작용 테스트 (Selenium) - hover인지 확인
    test_hover_interaction()
    
    # Click 상호작용 테스트 (Selenium) - click인지 확인
    test_click_interaction("https://ssadagu.kr", "ssadagu")
    
    # 빈 HTML 테스트
    # test_empty_html()  # 주석 처리
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60 + "\n")


