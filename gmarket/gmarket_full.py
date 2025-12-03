import time
import random
import re
import json
from typing import List, Dict
from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, SessionNotCreatedException


# ============================================================
# 0) 드라이버 종료 시 WinError 6 무시
# ============================================================
if hasattr(uc.Chrome, "__del__"):
    uc.Chrome.__del__ = lambda self: None


# ============================================================
# 1) 전체 카테고리 경로 (실제 크롤링용)
# ============================================================
CATEGORY_PATHS: List[list[str]] = [
    ["브랜드패션", "브랜드여성의류"],
    ["브랜드패션", "브랜드남성의류"],
    ["브랜드패션", "브랜드캐주얼의류"],
    ["브랜드패션", "브랜드잡화"],
    ["브랜드패션", "브랜드 쥬얼리/시계"],
    ["브랜드패션", "수입명품"],
    ["브랜드패션", "브랜드 아웃도어"],
    ["브랜드패션", "브랜드 스포츠패션"],

    ["패션의류 잡화 뷰티", "여성의류"],
    ["패션의류 잡화 뷰티", "남성의류"],
    ["패션의류 잡화 뷰티", "언더웨어"],
    ["패션의류 잡화 뷰티", "유아동의류"],
    ["패션의류 잡화 뷰티", "신발"],
    ["패션의류 잡화 뷰티", "가방/잡화"],
    ["패션의류 잡화 뷰티", "유아동 신발/잡화"],
    ["패션의류 잡화 뷰티", "쥬얼리/시계"],
    ["패션의류 잡화 뷰티", "수입명품"],
    ["패션의류 잡화 뷰티", "화장품/향수"],
    ["패션의류 잡화 뷰티", "바디/헤어"],

    ["유아동", "출산/육아"],
    ["유아동", "장난감/완구"],
    ["유아동", "유아동 의류"],
    ["유아동", "유아동 신발/잡화"],

    ["식품 생필품", "신선식품"],
    ["식품 생필품", "가공식품"],
    ["식품 생필품", "건강식품"],
    ["식품 생필품", "커피/음료"],
    ["식품 생필품", "생필품"],
    ["식품 생필품", "바디/헤어"],

    ["홈데코 문구 취미 반려", "가구/DIY"],
    ["홈데코 문구 취미 반려", "침구/커튼"],
    ["홈데코 문구 취미 반려", "조명/인테리어"],
    ["홈데코 문구 취미 반려", "생활용품"],
    ["홈데코 문구 취미 반려", "주방용품"],
    ["홈데코 문구 취미 반려", "꽃/이벤트용품"],
    ["홈데코 문구 취미 반려", "문구/사무용품"],
    ["홈데코 문구 취미 반려", "사무기기"],
    ["홈데코 문구 취미 반려", "악기/취미"],
    ["홈데코 문구 취미 반려", "반려동물용품"],

    ["컴퓨터 디지털 가전", "노트북/데스크탑"],
    ["컴퓨터 디지털 가전", "모니터/프린터"],
    ["컴퓨터 디지털 가전", "PC주변기기"],
    ["컴퓨터 디지털 가전", "저장장치"],
    ["컴퓨터 디지털 가전", "모바일/태블릿"],
    ["컴퓨터 디지털 가전", "카메라"],
    ["컴퓨터 디지털 가전", "게임"],
    ["컴퓨터 디지털 가전", "음향기기"],
    ["컴퓨터 디지털 가전", "영상가전"],
    ["컴퓨터 디지털 가전", "주방가전"],
    ["컴퓨터 디지털 가전", "계절가전"],
    ["컴퓨터 디지털 가전", "생활/미용가전"],
    ["컴퓨터 디지털 가전", "음향가전"],
    ["컴퓨터 디지털 가전", "건강가전"],

    ["스포츠 건강 렌탈", "스포츠의류/운동화"],
    ["스포츠 건강 렌탈", "휘트니스/수영"],
    ["스포츠 건강 렌탈", "구기/라켓"],
    ["스포츠 건강 렌탈", "골프"],
    ["스포츠 건강 렌탈", "자저거/보드/기타레저"],
    ["스포츠 건강 렌탈", "캠핑/낚시"],
    ["스포츠 건강 렌탈", "등산/아웃도어"],
    ["스포츠 건강 렌탈", "건강/의료용품"],
    ["스포츠 건강 렌탈", "건강식품"],
    ["스포츠 건강 렌탈", "렌탈 서비스"],
    ["스포츠 건강 렌탈", "상조"],
    ["스포츠 건강 렌탈", "인터넷가입"],

    ["자동차 공구", "자동차용품"],
    ["자동차 공구", "공구/안전/산업용품"],
]


# ============================================================
# 2) 테스트용 (브랜드 여성의류만)
# ============================================================
CATEGORY_PATHS_TEST = [
    ["브랜드패션", "브랜드여성의류"],
]


# ============================================================
# 3) 공통 함수들
# ============================================================
def setup_driver(headless=False) -> uc.Chrome:
    def make_options():
        opt = uc.ChromeOptions()
        opt.add_argument("--disable-blink-features=AutomationControlled")
        opt.add_argument("--disable-infobars")
        opt.add_argument("--disable-extensions")
        opt.add_argument("--disable-popup-blocking")
        opt.add_argument("--no-sandbox")
        opt.add_argument("--disable-dev-shm-usage")
        opt.add_argument("--lang=ko-KR")
        if headless:
            opt.add_argument("--headless=new")
            opt.add_argument("--window-size=1400,900")
        return opt

    try:
        driver = uc.Chrome(options=make_options())
    except SessionNotCreatedException:
        print("[WARN] 기본 Chrome 실행 실패 → version_main=142 강제 적용")
        driver = uc.Chrome(options=make_options(), version_main=142)

    driver.implicitly_wait(4)
    return driver


def wait_visible(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
    except:
        return None


def click_element(driver, el):
    try:
        el.click()
    except:
        driver.execute_script("arguments[0].click();", el)


def normalize_label(s):
    # 공백 + 점/중점(·)/슬래시 같은 기호 다 날리고 한글/영문/숫자만 비교
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s or "")


def check_blocked(driver):
    html = driver.page_source
    for k in ["Sorry, you have been blocked", "봇으로", "Access Denied"]:
        if k in html:
            raise RuntimeError("G마켓에서 접속 차단됨")


# ============================================================
# 4) 전체 카테고리 패널 열기
# ============================================================
def open_category_panel(driver):
    driver.get("https://www.gmarket.co.kr/")
    time.sleep(2)
    check_blocked(driver)

    btn = wait_visible(driver, By.CSS_SELECTOR, "#button__category-all", 5)
    if not btn:
        btn = wait_visible(driver,
                           By.CSS_SELECTOR,
                           "button[aria-controls='box__category-all-layer']",
                           5)
    if not btn:
        raise RuntimeError("전체카테고리 버튼 발견 실패")

    click_element(driver, btn)
    time.sleep(1.5)


# ============================================================
# 5) 1차/2차 페이지 진입
# ============================================================
def go_to_level2(driver, l1, l2):
    target_l1 = normalize_label(l1)
    target_l2 = normalize_label(l2)

    open_category_panel(driver)
    panel = wait_visible(driver, By.ID, "box__category-all-layer", 5)

    # 1차 찾기
    anchors = panel.find_elements(By.TAG_NAME, "a")
    l1_el = None
    for a in anchors:
        if normalize_label(a.text.strip()) == target_l1:
            l1_el = a
            break
    if not l1_el:
        raise RuntimeError(f"1차 '{l1}' 찾기 실패")

    ActionChains(driver).move_to_element(l1_el).perform()
    time.sleep(0.8)

    # 2차 찾기
    anchors = panel.find_elements(By.TAG_NAME, "a")
    l2_el = None
    for a in anchors:
        if normalize_label(a.text.strip()) == target_l2:
            l2_el = a
            break

    if not l2_el:
        raise RuntimeError(f"2차 '{l2}' 찾기 실패")

    click_element(driver, l2_el)
    time.sleep(2)
    check_blocked(driver)


# ============================================================
# 6) LNB에서 3차 카테고리 자동 수집
# ============================================================
def get_level3_from_lnb(driver, l1, l2):
    time.sleep(1.5)

    container = (
        wait_visible(driver, By.ID, "gnb", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div.left-area", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div.lnb", 2)
    )
    if not container:
        print(f"[INFO] LNB 없음 → 2차 '{l2}' 직접 수집")
        return [{
            "level1_name": l1,
            "level2_name": l2,
            "level3_name": l2,
            "url": driver.current_url
        }]

    links = container.find_elements(By.XPATH, ".//a[contains(@href,'category=')]")

    result = []
    seen = set()
    for a in links:
        name = a.text.strip()
        href = a.get_attribute("href") or ""
        if not name or not href:
            continue
        if (name, href) in seen:
            continue
        seen.add((name, href))
        result.append({
            "level1_name": l1,
            "level2_name": l2,
            "level3_name": name,
            "url": href
        })

    return result


# ============================================================
# 7) 3차 카테고리 상품 수집
# ============================================================
def clean_title(text):
    if not text:
        return None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    title = lines[-1]
    if len(title) < 4 or len(title) > 150:
        return None
    return title


def collect_products(driver, l1, l2, l3, url, max_items=60):
    driver.get(url)
    time.sleep(2)
    check_blocked(driver)

    # 스크롤
    for y in [200, 600, 1000, 1500, 2000]:
        driver.execute_script(f"window.scrollTo(0,{y});")
        time.sleep(0.8 + random.random())

    els = driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'item.gmarket.co.kr') and contains(@href,'goodscode=')]"
    )

    out = []
    seen = set()

    for el in els:
        try:
            t = el.text
        except:
            continue

        title = clean_title(t)
        if not title:
            continue

        href = el.get_attribute("href")
        if not href:
            continue

        key = (title, href)
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "level1_name": l1,
            "level2_name": l2,
            "level3_name": l3,
            "title": title,
            "url": href
        })

        if len(out) >= max_items:
            break

    print(f"[DEBUG] {l1} > {l2} > {l3}: {len(out)}개 수집")
    return out


# ============================================================
# 8) 전체 JSON 저장
# ============================================================
def save_json(products, base_dir="gmarket_data"):
    ts = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(base_dir) / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "products_all.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"[INFO] JSON 저장 완료 → {path}")


# ============================================================
# 9) 메인 파이프라인
# ============================================================
def main(headless=False, max_items=60, category_paths=None):
    if category_paths is None:
        category_paths = CATEGORY_PATHS

    driver = setup_driver(headless)
    all_items = []

    try:
        for l1, l2 in category_paths:
            print("\n" + "=" * 80)
            print(f"[INFO] 크롤링 시작 → {l1} > {l2}")
            print("=" * 80)

            try:
                go_to_level2(driver, l1, l2)
                level3_list = get_level3_from_lnb(driver, l1, l2)

                for leaf in level3_list:
                    l3 = leaf["level3_name"]
                    url = leaf["url"]

                    try:
                        prods = collect_products(driver, l1, l2, l3, url, max_items)
                        all_items.extend(prods)
                    except Exception as e:
                        print(f"[WARN] 3차 '{l3}' 수집 실패 → {e}")

            except Exception as e:
                print(f"[WARN] 경로 실패 → {l1} > {l2}: {e}")
                continue

    finally:
        try:
            driver.quit()
        except:
            pass

    return all_items


# ============================================================
# 10) 실행부
# ============================================================
if __name__ == "__main__":
    # 실제 전체 크롤링 실행
    products = main(
        headless=False,
        max_items=60,
        category_paths=CATEGORY_PATHS   # ← 전체 크롤링하려면 CATEGORY_PATHS 로 변경
    )

    save_json(products)

    print("\n=== 샘플 출력 ===")
    for i, p in enumerate(products[:20], start=1):
        print(f"{i:02d}. [{p['level1_name']} > {p['level2_name']} > {p['level3_name']}] {p['title']}")
        print("    ", p["url"])
