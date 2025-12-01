# 3단계 카테고리를 못 찾는 원인 분석

## 발견된 문제

### 핵심 문제점

**"신발/가방/패션잡화" > "남성의류" (또는 "여성의류") 같은 경우:**

1. ✅ **dep_3cover 요소는 발견됨**
2. ✅ **JavaScript로는 링크를 찾을 수 있음** (13개, 14개 등)
3. ❌ **`display: none`** - 3단계 메뉴가 `display: none`으로 숨겨져 있음
4. ❌ **`is_displayed(): False`** - Selenium이 상호작용 불가능으로 판단
5. ❌ **Selenium의 `text` 속성이 빈 문자열** - `display: none`인 요소의 텍스트는 읽을 수 없음

### 상세 분석 결과

```
4. CSS 속성 확인...
   - visibility: visible  ✅
   - display: none        ❌ ← 문제!
   - opacity: 1
   - height: 100%
   - width: 100%
   - is_displayed(): False  ❌ ← 문제!

6. 3단계 링크 찾기...
   방법 1 (li.dep_3 > a.cate_tit): 13개  ✅ (요소는 찾음)
   방법 4 (JavaScript): 13개  ✅ (JavaScript로는 텍스트도 읽을 수 있음)
     1. 셔츠 (https://ssadagu.kr/shop/search.php?ss_tx=...)
     2. 티셔츠 (https://ssadagu.kr/shop/search.php?ss_tx=...)
     ...
   
   텍스트가 있는 링크: 0개  ❌ ← 문제!

7. 조건 체크 결과...
   - visibility == 'visible': True  ✅
   - display != 'none': False       ❌ ← 여기서 걸림!
   - is_displayed(): False          ❌
   - 모든 조건 만족: False          ❌
```

## 문제의 원인

### 1. **`display: none` 문제**
- 3단계 메뉴가 `display: none`으로 숨겨져 있음
- 현재 코드는 `display != "none"` 조건을 체크하므로 실패
- 하지만 JavaScript로는 DOM에 접근 가능하고 텍스트도 읽을 수 있음

### 2. **Selenium의 `text` 속성 제한**
- `display: none`인 요소의 `text` 속성은 빈 문자열 반환
- Selenium은 "보이는 텍스트"만 읽을 수 있음
- 하지만 JavaScript의 `textContent`나 `innerText`는 DOM의 실제 텍스트를 읽을 수 있음

### 3. **조건 체크 로직의 문제**
```python
# 현재 코드
if dep3_visible == "visible" and dep3_display != "none" and dep3_is_displayed:
    # 3단계 탐색 진행
```

- `display: none`이면 이 조건을 통과하지 못함
- 하지만 JavaScript로는 링크를 찾을 수 있고 텍스트도 읽을 수 있음

## 해결 방안 (코드 수정 전)

### 방안 1: JavaScript로 텍스트 가져오기 (추천)
```python
# Selenium의 text 속성 대신 JavaScript로 텍스트 가져오기
dep3_links_js = driver.execute_script("""
    var container = arguments[0];
    var links = container.querySelectorAll('li.dep_3 > a.cate_tit');
    var result = [];
    for (var i = 0; i < links.length; i++) {
        var text = links[i].textContent.trim();
        if (text) {
            result.push({
                element: links[i],
                text: text,
                href: links[i].href
            });
        }
    }
    return result;
""", dep3_container)

# JavaScript로 가져온 정보 사용
for link_info in dep3_links_js:
    dep3_name = link_info['text']
    path = [dep1_name, dep2_name, dep3_name]
    all_paths.append(path)
```

### 방안 2: JavaScript로 강제 표시 후 텍스트 읽기
```python
# display를 block으로 변경
driver.execute_script(
    "arguments[0].style.display = 'block';",
    dep3_container
)
time.sleep(0.3)

# 이제 Selenium의 text 속성으로 읽을 수 있음
dep3_links = dep3_container.find_elements(By.CSS_SELECTOR, "li.dep_3 > a.cate_tit")
for link in dep3_links:
    text = link.text.strip()  # 이제 읽을 수 있음
```

### 방안 3: 조건 체크 완화
```python
# display: none이어도 JavaScript로 접근 가능하면 진행
if dep3_visible == "visible":
    # JavaScript로 링크 찾기
    dep3_links_js = driver.execute_script("""
        var container = arguments[0];
        return Array.from(container.querySelectorAll('li.dep_3 > a.cate_tit'))
            .map(link => link.textContent.trim())
            .filter(text => text);
    """, dep3_container)
    
    if dep3_links_js:
        # JavaScript로 찾은 텍스트 사용
        for dep3_name in dep3_links_js:
            path = [dep1_name, dep2_name, dep3_name]
            all_paths.append(path)
```

### 방안 4: `textContent` 속성 직접 사용
```python
# Selenium의 text 대신 JavaScript로 textContent 가져오기
for dep3_link in dep3_links:
    dep3_name = driver.execute_script(
        "return arguments[0].textContent.trim();",
        dep3_link
    )
    if dep3_name:
        path = [dep1_name, dep2_name, dep3_name]
        all_paths.append(path)
```

## 권장 해결 순서

1. **방안 1 (JavaScript로 텍스트 가져오기)** - 가장 안전하고 확실
   - `display: none` 상태에서도 작동
   - 텍스트와 href를 모두 가져올 수 있음
   - 추가 DOM 조작 불필요

2. **방안 2 (강제 표시 후 읽기)** - 보조 방법
   - 필요시 사용
   - 하지만 사이트 구조를 변경할 수 있으므로 주의

3. **방안 4 (textContent 직접 사용)** - 간단한 방법
   - 각 링크마다 JavaScript 실행
   - 방안 1보다는 느릴 수 있음

## 추가 확인 사항

1. **왜 일부 카테고리는 작동하고 일부는 안 되는가?**
   - "패션의류/이너웨어" > "남성의류"는 작동함 (이미 찾은 경로)
   - "신발/가방/패션잡화" > "여성슈즈"는 안 됨
   - 사이트 구조가 카테고리마다 다를 수 있음

2. **hover 타이밍 문제일 수도 있음**
   - 일부 카테고리는 더 긴 대기 시간이 필요할 수 있음
   - 하지만 현재 1.5초 대기로도 충분해 보임

3. **실제로 3단계가 없는 경우도 있을 수 있음**
   - 일부 2단계 항목은 3단계가 없을 수 있음
   - 하지만 "여성슈즈" 같은 경우는 분명히 3단계가 있음 (사용자가 제공한 HTML에서 확인)



