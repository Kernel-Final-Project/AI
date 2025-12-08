# coupang/coupang_crawl.py

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
# 1) 1차/2차 카테고리 + 2차 URL (하드코딩)
#    - level1_name / level2_name / url
# ============================================================
CATEGORY_PATHS: List[Dict[str, str]] = [
    # 패션의류/잡화
    {"level1": "패션의류/잡화", "level2": "여성패션", "url": "https://www.coupang.com/np/categories/186764"},
    {"level1": "패션의류/잡화", "level2": "남성패션", "url": "https://www.coupang.com/np/categories/187069"},
    {"level1": "패션의류/잡화", "level2": "남녀 공용 의류", "url": "https://www.coupang.com/np/categories/502993"},
    {"level1": "패션의류/잡화", "level2": "속옷/잠옷", "url": "https://www.coupang.com/np/categories/565063"},
    {"level1": "패션의류/잡화", "level2": "신발", "url": "https://www.coupang.com/np/campaigns/20497"},
    {"level1": "패션의류/잡화", "level2": "가방/잡화", "url": "https://www.coupang.com/np/campaigns/20495"},
    {"level1": "패션의류/잡화", "level2": "유아동패션", "url": "https://www.coupang.com/np/categories/213201"},
    {"level1": "패션의류/잡화", "level2": "럭셔리패션", "url": "https://www.coupang.com/np/campaigns/22131"},

    # 뷰티
    {"level1": "뷰티", "level2": "신상관", "url": "https://www.coupang.com/np/campaigns/22455"},
    {"level1": "뷰티", "level2": "럭셔리뷰티", "url": "https://www.coupang.com/np/campaigns/18530"},
    {"level1": "뷰티", "level2": "스킨케어", "url": "https://www.coupang.com/np/categories/176530"},
    {"level1": "뷰티", "level2": "클렌징/필링", "url": "https://www.coupang.com/np/categories/486551"},
    {"level1": "뷰티", "level2": "선케어/태닝", "url": "https://www.coupang.com/np/categories/176563"},
    {"level1": "뷰티", "level2": "더마코스메틱", "url": "https://www.coupang.com/np/campaigns/7642"},
    {"level1": "뷰티", "level2": "메이크업", "url": "https://www.coupang.com/np/categories/176573"},
    {"level1": "뷰티", "level2": "향수", "url": "https://www.coupang.com/np/categories/176598"},
    {"level1": "뷰티", "level2": "남성화장품", "url": "https://www.coupang.com/np/categories/176839"},
    {"level1": "뷰티", "level2": "네일", "url": "https://www.coupang.com/np/categories/176763"},
    {"level1": "뷰티", "level2": "뷰티소품", "url": "https://www.coupang.com/np/categories/176807"},
    {"level1": "뷰티", "level2": "어린이화장품", "url": "https://www.coupang.com/np/categories/403012"},
    {"level1": "뷰티", "level2": "로드샵", "url": "https://www.coupang.com/np/campaigns/4999"},
    {"level1": "뷰티", "level2": "클린/비건뷰티", "url": "https://www.coupang.com/np/categories/509393"},
    {"level1": "뷰티", "level2": "헤어", "url": "https://www.coupang.com/np/categories/176602"},
    {"level1": "뷰티", "level2": "바디", "url": "https://www.coupang.com/np/categories/176699"},
    {"level1": "뷰티", "level2": "선물세트/키트", "url": "https://www.coupang.com/np/categories/176963"},

    # 식품
    {"level1": "식품", "level2": "수입식품관", "url": "https://www.coupang.com/np/campaigns/1884"},
    {"level1": "식품", "level2": "식품 선물세트", "url": "https://www.coupang.com/np/categories/196393"},
    {"level1": "식품", "level2": "건강식품", "url": "https://www.coupang.com/np/categories/196076"},
    {"level1": "식품", "level2": "생수/음료", "url": "https://www.coupang.com/np/categories/195006"},
    {"level1": "식품", "level2": "커피/원두/차", "url": "https://www.coupang.com/np/categories/195142"},
    {"level1": "식품", "level2": "과자/초콜릿/시리얼", "url": "https://www.coupang.com/np/categories/195266"},
    {"level1": "식품", "level2": "견과/건과", "url": "https://www.coupang.com/np/categories/194373"},
    {"level1": "식품", "level2": "반찬/간편식/대용식", "url": "https://www.coupang.com/np/categories/432480"},
    {"level1": "식품", "level2": "면/통조림/가공식품", "url": "https://www.coupang.com/np/categories/195443"},
    {"level1": "식품", "level2": "가루/조미료/오일", "url": "https://www.coupang.com/np/categories/195576"},
    {"level1": "식품", "level2": "장/소스/드레싱/식초", "url": "https://www.coupang.com/np/categories/195694"},
    {"level1": "식품", "level2": "냉장/냉동/간편요리", "url": "https://www.coupang.com/np/categories/225461"},
    {"level1": "식품", "level2": "과일", "url": "https://www.coupang.com/np/categories/194282"},
    {"level1": "식품", "level2": "축산/계란", "url": "https://www.coupang.com/np/categories/194688"},
    {"level1": "식품", "level2": "채소", "url": "https://www.coupang.com/np/categories/194432"},
    {"level1": "식품", "level2": "수산물/건어물", "url": "https://www.coupang.com/np/categories/194829"},
    {"level1": "식품", "level2": "쌀/잡곡", "url": "https://www.coupang.com/np/categories/194627"},
    {"level1": "식품", "level2": "유제품/아이스크림", "url": "https://www.coupang.com/np/categories/195783"},
    {"level1": "식품", "level2": "유기농/친환경", "url": "https://www.coupang.com/np/campaigns/10076"},

    # 주방용품
    {"level1": "주방용품", "level2": "냄비/프라이팬", "url": "https://www.coupang.com/np/categories/185671"},
    {"level1": "주방용품", "level2": "주방조리도구", "url": "https://www.coupang.com/np/categories/185976"},
    {"level1": "주방용품", "level2": "그릇/홈세트", "url": "https://www.coupang.com/np/categories/185735"},
    {"level1": "주방용품", "level2": "컵/텀블러/와인용품", "url": "https://www.coupang.com/np/categories/185797"},
    {"level1": "주방용품", "level2": "밀폐저장/도시락", "url": "https://www.coupang.com/np/categories/185872"},
    {"level1": "주방용품", "level2": "수저/커트러리", "url": "https://www.coupang.com/np/categories/185823"},
    {"level1": "주방용품", "level2": "주방잡화", "url": "https://www.coupang.com/np/categories/399678"},
    {"level1": "주방용품", "level2": "주방수납/정리", "url": "https://www.coupang.com/np/categories/186147"},
    {"level1": "주방용품", "level2": "주전자/커피/티용품", "url": "https://www.coupang.com/np/categories/186412"},
    {"level1": "주방용품", "level2": "일회용품/종이컵", "url": "https://www.coupang.com/np/categories/186260"},
    {"level1": "주방용품", "level2": "주방가전", "url": "https://www.coupang.com/np/categories/186504"},
    {"level1": "주방용품", "level2": "보온/보냉용품", "url": "https://www.coupang.com/np/categories/185955"},

    # 생활용품
    {"level1": "생활용품", "level2": "헤어", "url": "https://www.coupang.com/np/categories/123111"},
    {"level1": "생활용품", "level2": "바디/세안", "url": "https://www.coupang.com/np/categories/509357"},
    {"level1": "생활용품", "level2": "구강/면도", "url": "https://www.coupang.com/np/categories/114471"},
    {"level1": "생활용품", "level2": "화장지/물티슈", "url": "https://www.coupang.com/np/categories/465071"},
    {"level1": "생활용품", "level2": "생리대/성인용기저귀", "url": "https://www.coupang.com/np/categories/465072"},
    {"level1": "생활용품", "level2": "기저귀", "url": "https://www.coupang.com/np/categories/502258"},
    {"level1": "생활용품", "level2": "세탁세제", "url": "https://www.coupang.com/np/categories/399742"},
    {"level1": "생활용품", "level2": "청소/주방세제", "url": "https://www.coupang.com/np/categories/399758"},
    {"level1": "생활용품", "level2": "탈취/방향/살충", "url": "https://www.coupang.com/np/categories/114472"},
    {"level1": "생활용품", "level2": "건강/의료옹품", "url": "https://www.coupang.com/np/categories/114473"},
    {"level1": "생활용품", "level2": "세탁/청소용품", "url": "https://www.coupang.com/np/categories/225844"},
    {"level1": "생활용품", "level2": "욕실용품", "url": "https://www.coupang.com/np/categories/419509"},
    {"level1": "생활용품", "level2": "생활전기용품", "url": "https://www.coupang.com/np/categories/399909"},
    {"level1": "생활용품", "level2": "수납/정리", "url": "https://www.coupang.com/np/categories/114727"},
    {"level1": "생활용품", "level2": "주방수납/잡화", "url": "https://www.coupang.com/np/categories/105903"},
    {"level1": "생활용품", "level2": "생활잡화", "url": "https://www.coupang.com/np/categories/114729"},
]


# 테스트용 간단 버전 (예: 여성패션만)
CATEGORY_PATHS_TEST: List[Dict[str, str]] = [
    {"level1": "패션의류/잡화", "level2": "여성패션", "url": "https://www.coupang.com/np/categories/186764"},
]


# ============================================================
# 2) 공통 유틸
# ============================================================
def setup_driver(headless: bool = False) -> uc.Chrome:
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
    except TimeoutException:
        return None


def click_element(driver, el):
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def extract_product_code(product_url: str) -> str | None:
    """
    /vp/products/8333951287?itemId=... 에서 8333951287 추출
    """
    if not product_url:
        return None
    m = re.search(r"/products/(\d+)", product_url)
    if not m:
        return None
    return m.group(1)


def ensure_abs_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.coupang.com" + url
    return url


# ============================================================
# 3) 3차 카테고리 자동 수집 (카테고리 박스 한정 + 로켓류 필터링)
# ============================================================
BAD_LEVEL3_KEYWORDS = ["로켓", "프레시", "로켓프레시", "로켓직구", "로켓와우"]

def get_level3_categories(driver, level1: str, level2: str, level2_url: str) -> List[Dict]:
    """
    2차 카테고리 URL에서 왼쪽 '카테고리' 영역 안의 3차 카테고리 링크만 수집
    - href 가 /np/categories/ 로 시작하는 a 태그
    - 로켓프레시/로켓배송 같은 필터는 이름에 '로켓' 등이 들어가서 제외
    """
    driver.get(level2_url)
    time.sleep(2 + random.random())

    # 한 번 스크롤해서 레이아웃 안정화
    driver.execute_script("window.scrollTo(0, 300);")
    time.sleep(1)

    container = None

    # 1) '카테고리' 제목이 있는 박스를 찾아본다.
    xpaths = [
        # 검색결과 페이지 좌측 필터 영역에 많이 쓰이는 패턴들 추측
        "//div[.//span[text()='카테고리']]",
        "//div[.//h3[contains(text(),'카테고리')]]",
        "//section[.//span[text()='카테고리']]",
    ]

    for xp in xpaths:
        try:
            container = driver.find_element(By.XPATH, xp)
            break
        except Exception:
            continue

    links = []
    if container is not None:
        # 카테고리 박스 안에서만 3차 링크 수집
        links = container.find_elements(
            By.XPATH,
            ".//a[contains(@href,'/np/categories/')]"
        )
    else:
        # 혹시 위 XPATH 가 다 실패하면 예전 방식으로 fallback (그래도 나중에 필터 한 번 더 걸어줌)
        print(f"[INFO] '카테고리' 컨테이너 탐색 실패 → fallback 전체 링크 스캔 ({level1} > {level2})")
        links = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href^='https://www.coupang.com/np/categories/']"
        )

    results: List[Dict] = []
    seen = set()

    for a in links:
        name = normalize_space(a.text)
        href = a.get_attribute("href") or ""
        if not name or not href:
            continue

        # 로켓/로켓프레시 같은 필터는 제외
        if any(bad in name for bad in BAD_LEVEL3_KEYWORDS):
            continue

        key = (name, href)
        if key in seen:
            continue
        seen.add(key)

        results.append(
            {
                "level1_name": level1,
                "level2_name": level2,
                "level3_name": name,
                "url": href,
            }
        )

    if not results:
        # 3차 메뉴가 아예 없으면 2차 자체를 leaf로 사용
        results.append(
            {
                "level1_name": level1,
                "level2_name": level2,
                "level3_name": level2,
                "url": level2_url,
            }
        )

    print(f"[DEBUG] 3차 카테고리 {len(results)}개 발견: {level1} > {level2}")
    return results



# ============================================================
# 4) 상품 리스트 페이지에서 상품들 수집 (1페이지만)
# ============================================================
def collect_products_in_page(
    driver,
    level1: str,
    level2: str,
    level3: str,
    url: str,
) -> List[Dict]:
    """
    3차 카테고리 1페이지에서 상품 카드 수집
    - li[class*='ProductUnit_productUnit'] 기준
    """
    driver.get(url)
    time.sleep(2 + random.random())

    # 스크롤 몇 번 내려서 lazy-load 유도
    for y in [400, 1000, 1600, 2200]:
        driver.execute_script(f"window.scrollTo(0, {y});")
        time.sleep(0.8 + random.random())

    items: List[Dict] = []

    # 상품 카드 li
    product_lis = driver.find_elements(
        By.CSS_SELECTOR,
        "li[class*='ProductUnit_productUnit']",
    )

    for li in product_lis:
        try:
            a = li.find_element(By.CSS_SELECTOR, "a[href*='/vp/products/']")
        except Exception:
            continue

        product_url = ensure_abs_url(a.getAttribute("href") if hasattr(a, "getAttribute") else a.get_attribute("href"))
        product_code = extract_product_code(product_url)

        # 이미지
        img_el = None
        try:
            img_el = li.find_element(By.CSS_SELECTOR, "figure[class*='ProductUnit_productImage'] img")
        except Exception:
            try:
                img_el = li.find_element(By.CSS_SELECTOR, "img")
            except Exception:
                img_el = None
        image_url = ensure_abs_url(img_el.get_attribute("src")) if img_el else ""

        # 상품명
        name_el = None
        try:
            name_el = li.find_element(By.CSS_SELECTOR, "div[class^='ProductUnit_productName']")
        except Exception:
            try:
                name_el = li.find_element(By.CSS_SELECTOR, "div.ProductUnit_productNameV2__cV9cw")
            except Exception:
                name_el = None
        product_name = normalize_space(name_el.text if name_el else "")

        # 가격
        price_el = None
        try:
            price_el = li.find_element(By.CSS_SELECTOR, "strong[class^='Price_priceValue']")
        except Exception:
            price_el = None
        product_price = normalize_space(price_el.text if price_el else "")

        if not product_name or not product_url:
            continue

        items.append(
            {
                "level1_name": level1,
                "level2_name": level2,
                "level3_name": level3,
                "product_code": product_code,
                "product_name": product_name,
                "product_price": product_price,
                "image_url": image_url,
                "product_url": product_url,
            }
        )

    print(f"[DEBUG] {level1} > {level2} > {level3}: {len(items)}개 수집 (1페이지)")
    return items


# ============================================================
# 5) JSON 저장
# ============================================================
def save_json(products: List[Dict], base_dir: str = "coupang_data") -> Path:
    ts = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(base_dir) / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / "products_all.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"[INFO] JSON 저장 완료 → {path}")
    return path


# ============================================================
# 6) 메인 파이프라인
# ============================================================
def main(
    headless: bool = False,
    category_paths: List[Dict[str, str]] | None = None,
    max_level3_per_level2: int | None = None,
) -> List[Dict]:
    """
    - headless: 브라우저 숨김 여부
    - category_paths: 기본은 위에 정의한 CATEGORY_PATHS
    - max_level3_per_level2: 디버깅용으로 3차 카테고리 일부만 돌리고 싶을 때
    """
    if category_paths is None:
        category_paths = CATEGORY_PATHS

    driver = setup_driver(headless=headless)
    all_products: List[Dict] = []

    try:
        for cp in category_paths:
            level1 = cp["level1"]
            level2 = cp["level2"]
            url2 = cp["url"]

            print("\n" + "=" * 80)
            print(f"[INFO] 크롤링 시작 → {level1} > {level2}")
            print("=" * 80)

            try:
                # 3차 카테고리들 자동 수집
                level3_list = get_level3_categories(driver, level1, level2, url2)

                if max_level3_per_level2 is not None:
                    level3_list = level3_list[:max_level3_per_level2]

                for leaf in level3_list:
                    l3 = leaf["level3_name"]
                    url3 = leaf["url"]

                    try:
                        products = collect_products_in_page(
                            driver,
                            level1,
                            level2,
                            l3,
                            url3,
                        )
                        all_products.extend(products)
                    except Exception as e:
                        print(f"[WARN] 3차 '{l3}' 수집 실패 → {e}")

            except Exception as e:
                print(f"[WARN] {level1} > {level2} 처리 중 예외 → {e}")
                continue

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\n[INFO] 전체 상품 수: {len(all_products)}")
    return all_products


# ============================================================
# 7) 실행부
# ============================================================
if __name__ == "__main__":
    # 우선 테스트할 땐 CATEGORY_PATHS_TEST + max_level3_per_level2=2 이런 식으로 가볍게 돌려봐
    products = main(
        headless=False,
        category_paths=CATEGORY_PATHS_TEST,   # 전체 돌릴 땐 CATEGORY_PATHS 로 교체
        max_level3_per_level2=2,             # 디버깅용(원하면 None 으로)
    )

    save_json(products)

    print("\n=== 샘플 20개 ===")
    for i, p in enumerate(products[:20], start=1):
        print(
            f"{i:02d}. [{p['level1_name']} > {p['level2_name']} > {p['level3_name']}] "
            f"{p['product_name']} | {p['product_price']}"
        )
        print("    code:", p["product_code"], "url:", p["product_url"])
