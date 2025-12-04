# ============================================================
# G마켓 전체 카테고리 크롤링 (A안)
#  - 1차 / 2차 카테고리 : 하드코딩
#  - 3차 카테고리       : LNB 자동탐색
#  - 상품 정보           : 코드 / 이름 / 가격 / 이미지 / URL
#  - 저장 형식           : 팀원 JSON 템플릿 + 카테고리 정보
#
# 실행 예:
#   (venv) python gmarket/gmarket_crawl.py
#
# 결과:
#   gmarket_data/2025-12-03/products_all_final.json
# ============================================================

import time
import re
import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    SessionNotCreatedException,
)


# ------------------------------------------------------------
# 드라이버 종료 WinError 6 무시
# ------------------------------------------------------------
if hasattr(uc.Chrome, "__del__"):
    uc.Chrome.__del__ = lambda self: None


# ------------------------------------------------------------
# 1차/2차 카테고리 전체 경로 (하드코딩)
#  - 네가 전에 정의한 목록 그대로 사용
# ------------------------------------------------------------
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
    ["스포츠 건강 렌탈", "자저거/보드/기타레저"],  # 여기 오타면 나중에 수정 가능
    ["스포츠 건강 렌탈", "캠핑/낚시"],
    ["스포츠 건강 렬탈", "등산/아웃도어"],         # (실패해도 로그만 찍고 지나감)
    ["스포츠 건강 렬탈", "건강/의료용품"],
    ["스포츠 건강 렬탈", "건강식품"],
    ["스포츠 건강 렬탈", "렌탈 서비스"],
    ["스포츠 건강 렬탈", "상조"],
    ["스포츠 건강 렬탈", "인터넷가입"],

    ["자동차 공구", "자동차용품"],
    ["자동차 공구", "공구/안전/산업용품"],
]


# ------------------------------------------------------------
# 드라이버 생성
# ------------------------------------------------------------
def setup_driver(headless=False):
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
        print("[WARN] 기본 Chrome 실패 → version_main=142 강제 적용")
        driver = uc.Chrome(options=make_options(), version_main=142)

    driver.implicitly_wait(3)
    return driver


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def wait_visible(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
    except TimeoutException:
        return None


def click_element(driver, el):
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def normalize_label(s):
    # 공백 / 특수문자 제거해서 비교용으로 사용
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s or "")


def check_blocked(driver):
    html = driver.page_source
    bad = ["봇으로", "blocked", "Access Denied", "Sorry, you have been blocked"]
    if any(k in html for k in bad):
        raise RuntimeError("G마켓 접근 차단됨")


# ------------------------------------------------------------
#  전체카테고리 패널 열기
# ------------------------------------------------------------
def open_category_panel(driver, retry=True):
    driver.get("https://www.gmarket.co.kr/")
    time.sleep(2)
    check_blocked(driver)

    btn = wait_visible(driver, By.CSS_SELECTOR, "#button__category-all", 5)
    if not btn:
        btn = wait_visible(
            driver,
            By.CSS_SELECTOR,
            "button[aria-controls='box__category-all-layer']",
            5,
        )
    if not btn:
        # 광고/팝업 등에 가려졌을 수 있으니 한 번 더 시도
        if retry:
            print("[WARN] 전체카테고리 버튼 못 찾음 → 한 번 더 재시도")
            return open_category_panel(driver, retry=False)
        raise RuntimeError("전체카테고리 버튼 발견 실패")

    click_element(driver, btn)
    time.sleep(1.5)

    panel = wait_visible(driver, By.ID, "box__category-all-layer", 5)
    if not panel and retry:
        print("[WARN] 카테고리 패널 못 찾음 → 홈 재로드 후 재시도")
        return open_category_panel(driver, retry=False)
    if not panel:
        raise RuntimeError("카테고리 패널 찾기 실패")

    return panel


# ------------------------------------------------------------
# 1차/2차 페이지 진입
# ------------------------------------------------------------
def go_to_level2(driver, level1_name: str, level2_name: str):
    target_l1 = normalize_label(level1_name)
    target_l2 = normalize_label(level2_name)

    panel = open_category_panel(driver)
    if not panel:
        raise RuntimeError("카테고리 패널 찾기 실패")

    # 1차 anchor 찾기
    anchors = panel.find_elements(By.TAG_NAME, "a")
    l1_el = None
    for a in anchors:
        txt = a.text.strip()
        if normalize_label(txt) == target_l1:
            l1_el = a
            break

    if not l1_el:
        raise RuntimeError(f"1차 '{level1_name}' 찾기 실패")

    # 마우스 오버 → 오른쪽 2차 뜨게
    try:
        ActionChains(driver).move_to_element(l1_el).perform()
    except Exception:
        click_element(driver, l1_el)
    time.sleep(0.8)

    # 다시 panel 기준으로 2차 anchor 찾기
    anchors = panel.find_elements(By.TAG_NAME, "a")
    l2_el = None
    for a in anchors:
        txt = a.text.strip()
        if normalize_label(txt) == target_l2:
            l2_el = a
            break

    if not l2_el:
        raise RuntimeError(f"2차 '{level2_name}' 찾기 실패")

    click_element(driver, l2_el)
    time.sleep(2)
    check_blocked(driver)

    print(f"[DEBUG] 이동 완료: {level1_name} > {level2_name} → {driver.current_url}")


# ------------------------------------------------------------
# LNB에서 3차 카테고리 자동 수집
# ------------------------------------------------------------
def get_level3_from_lnb(driver, l1: str, l2: str) -> List[Dict]:
    time.sleep(1.5)

    container = (
        wait_visible(driver, By.ID, "gnb", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div.left-area", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div.lnb", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div#categoryleft", 2)
        or wait_visible(driver, By.CSS_SELECTOR, "div#aside", 2)
    )

    if not container:
        print(f"[INFO] LNB 없음 → 2차 '{l2}' 자체를 leaf 로 사용")
        return [
            {
                "level1_name": l1,
                "level2_name": l2,
                "level3_name": l2,
                "url": driver.current_url,
            }
        ]

    links = container.find_elements(By.XPATH, ".//a[contains(@href,'category=')]")

    results: List[Dict] = []
    seen = set()

    for a in links:
        name = a.text.strip()
        href = a.get_attribute("href") or ""
        if not name or not href:
            continue
        key = (name, href)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "level1_name": l1,
                "level2_name": l2,
                "level3_name": name,
                "url": href,
            }
        )

    print(f"[DEBUG] 3차 leaf {len(results)}개 발견: {l1} > {l2}")
    return results


# ------------------------------------------------------------
# 상품 카드 하나에서 정보 추출
#   - product_code
#   - product_name
#   - product_price
#   - image_url
#   - product_url
# ------------------------------------------------------------
def parse_product_card(card, l1: str, l2: str, l3: str) -> Dict | None:
    # 1) 상품코드 (goodscode)
    product_code = None

    # (1) data-montelena-goodscode
    for a in card.find_elements(By.TAG_NAME, "a"):
        code = a.get_attribute("data-montelena-goodscode")
        if code and code.isdigit():
            product_code = code
            break

    # (2) href에서 goodscode= 추출
    if not product_code:
        for a in card.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            m = re.search(r"goodscode=(\d+)", href)
            if m:
                product_code = m.group(1)
                break

    if not product_code:
        # 코드 없으면 그냥 버린다 (팀원 포맷에서 code가 핵심이라)
        return None

    # 2) 상품명
    product_name = ""
    try:
        name_el = card.find_element(
            By.CSS_SELECTOR, ".box__item-title .text__item"
        )
        product_name = (name_el.get_attribute("title") or name_el.text).strip()
    except Exception:
        # fallback: 카드 전체에서 가장 마지막 줄 정도를 취해볼 수도 있음
        product_name = ""

    if not product_name:
        return None

    # 3) 가격 (쿠폰가/판매가 등 → 숫자 + '원')
    product_price = ""
    try:
        price_box = card.find_element(By.CSS_SELECTOR, ".box__item-price")
    except Exception:
        price_box = None

    if price_box:
        strong_el = None
        # (1) seller price strong
        try:
            strong_el = price_box.find_element(
                By.CSS_SELECTOR, ".box__price-seller strong.text__value"
            )
        except Exception:
            pass
        # (2) 그 외 strong.text__value
        if not strong_el:
            try:
                strong_el = price_box.find_element(
                    By.CSS_SELECTOR, "strong.text__value"
                )
            except Exception:
                pass
        # (3) span.text__value
        if not strong_el:
            try:
                strong_el = price_box.find_element(
                    By.CSS_SELECTOR, "span.text__value"
                )
            except Exception:
                pass

        if strong_el:
            price_num = strong_el.text.strip().replace(" ", "")
            if price_num:
                product_price = f"{price_num}원"

    if not product_price:
        # 가격이 전혀 안 잡히면 일단 None 반환 (원하면 남겨도 됨)
        return None

    # 4) 이미지 URL
    image_url = ""
    try:
        img_el = card.find_element(By.CSS_SELECTOR, ".box__image img.image__item")
        src = img_el.get_attribute("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        image_url = src
    except Exception:
        image_url = ""

    # 5) 상품 URL (canonical: goodscode 기반으로 생성)
    product_url = f"https://item.gmarket.co.kr/Item?goodscode={product_code}"

    # 팀원 포맷 + 카테고리 정보 같이 넣기
    return {
        "level1_name": l1,
        "level2_name": l2,
        "level3_name": l3,
        "product_code": product_code,
        "product_name": product_name,
        "product_price": product_price,
        "image_url": image_url,
        "product_url": product_url,
    }


# ------------------------------------------------------------
# 3차 카테고리(leaf) 별 상품 수집
# ------------------------------------------------------------
def collect_products_for_leaf(
    driver,
    l1: str,
    l2: str,
    l3: str,
    url: str,
    max_items: int,
    global_seen: set,
) -> List[Dict]:
    driver.get(url)
    time.sleep(2)
    check_blocked(driver)

    # 스크롤 내려서 lazy-load 유도
    for y in [200, 600, 1000, 1500, 2000, 2600, 3200]:
        driver.execute_script(f"window.scrollTo(0, {y});")
        time.sleep(0.7 + random.random())

    cards = driver.find_elements(By.CSS_SELECTOR, "div.box__item-container")

    products: List[Dict] = []
    for card in cards:
        item = parse_product_card(card, l1, l2, l3)
        if not item:
            continue

        key = (item["product_code"], l1, l2, l3)
        if key in global_seen:
            continue
        global_seen.add(key)

        products.append(item)

        if len(products) >= max_items:
            break

    print(
        f"[DEBUG] {l1} > {l2} > {l3}: {len(products)}개 수집 (URL={url})"
    )
    return products


# ------------------------------------------------------------
# JSON 저장 (팀원 템플릿 기반)
# ------------------------------------------------------------
def save_json(products, base_dir="gmarket_data"):
    ts = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(base_dir) / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    filepath = out_dir / "products_all_final.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 전체 JSON 저장 완료 → {filepath}")


# ------------------------------------------------------------
# 메인 파이프라인
# ------------------------------------------------------------
def main(
    headless: bool = False,
    max_items_per_leaf: int = 60,
    category_paths: List[list[str]] | None = None,
) -> List[Dict]:
    if category_paths is None:
        category_paths = CATEGORY_PATHS

    driver = setup_driver(headless=headless)
    all_products: List[Dict] = []
    global_seen: set = set()

    try:
        for idx, (l1, l2) in enumerate(category_paths, start=1):
            print("\n" + "=" * 80)
            print(f"[INFO] ({idx}/{len(category_paths)}) {l1} > {l2} 크롤링 시작")
            print("=" * 80)

            try:
                # 1차/2차 페이지 진입
                go_to_level2(driver, l1, l2)

                # 3차 LNB 자동 수집
                leaf_cats = get_level3_from_lnb(driver, l1, l2)

                # 각 3차 카테고리 순회
                for leaf in leaf_cats:
                    l3 = leaf["level3_name"]
                    url = leaf["url"]

                    try:
                        prods = collect_products_for_leaf(
                            driver,
                            leaf["level1_name"],
                            leaf["level2_name"],
                            l3,
                            url,
                            max_items=max_items_per_leaf,
                            global_seen=global_seen,
                        )
                        all_products.extend(prods)
                    except Exception as e:
                        print(
                            f"[WARN] 3차 '{l3}' 수집 중 예외 발생: {e}"
                        )
                        continue

            except Exception as e:
                print(f"[WARN] 경로 '{l1} > {l2}' 처리 실패: {e}")
                continue

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n[INFO] 전체 수집 상품 수: {len(all_products)}")
    return all_products


# ------------------------------------------------------------
# 실행부
# ------------------------------------------------------------
if __name__ == "__main__":
    # 필요하면 테스트용으로 일부 카테고리만 돌리고 싶을 때:
    # TEST_CATEGORY_PATHS = [["브랜드패션", "브랜드여성의류"]]
    # products = main(headless=False, max_items_per_leaf=40, category_paths=TEST_CATEGORY_PATHS)

    products = main(
        headless=False,
        max_items_per_leaf=60,
        category_paths=CATEGORY_PATHS,
    )

    save_json(products)

    print("\n=== 샘플 20개 ===")
    for i, p in enumerate(products[:20], start=1):
        print(
            f"{i:02d}. [{p['level1_name']} > {p['level2_name']} > {p['level3_name']}] "
            f"{p['product_name']} ({p['product_price']})"
        )
        print(f"    code={p['product_code']}  img={p['image_url']}")
        print(f"    url={p['product_url']}")
