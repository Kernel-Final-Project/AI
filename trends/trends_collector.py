"""
Google Trends 기반 이슈 상품 50개 수집 모듈
AI1 담당
"""
from __future__ import annotations

import inspect
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException,
                                        WebDriverException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.util.retry import Retry
from webdriver_manager.chrome import ChromeDriverManager


def _patch_urllib3_retry():
    parameters = inspect.signature(Retry.__init__).parameters
    if "method_whitelist" in parameters:
        return

    original_init = Retry.__init__

    def _patched_init(self, *args, **kwargs):
        if "method_whitelist" in kwargs and "allowed_methods" not in kwargs:
            kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
        original_init(self, *args, **kwargs)

    Retry.__init__ = _patched_init  # type: ignore


_patch_urllib3_retry()

from pytrends.request import TrendReq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.logger import logger
from storage import DataStorage


KST = timezone(timedelta(hours=9))
TREND_HL = "ko-KR"
TREND_TZ = 540  # UTC+9
TREND_GEO = "KR"
MIN_SCORE = 15
BAN_KEYWORDS = {
    "뉴스",
    "정치",
    "대선",
    "선거",
    "대통령",
    "총선",
    "사건",
    "사고",
    "사망",
    "지진",
    "환율",
    "주식",
    "비트코인",
    "사건",
    "날씨",
    "기상",
    "연예",
    "아이돌",
    "팬미팅",
    "무대",
}

TREND_DAILY_URL = "https://trends.google.co.kr/trending/trendingsearches/daily?geo=KR&hl=ko"
TREND_DAILY_API_URL = "https://trends.google.com/trends/api/dailytrends"
TREND_DAILY_WARMUP_URL = "https://trends.google.com/trending/trendingsearches/daily"
TREND_DAILY_API_TIMEOUT = (5, 25)
TREND_HTTP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]
SELENIUM_WAIT = 15
SELENIUM_LOAD_MORE_PAUSE = 2.5
DEFAULT_HEADLESS = os.getenv("SELENIUM_HEADLESS", "true").lower() not in {"false", "0", "no"}
TREND_PN = os.getenv("TREND_PN", "south_korea")
try:
    TRENDING_FETCH_LIMIT = max(1, int(os.getenv("TRENDING_FETCH_LIMIT", "50")))
except ValueError:
    TRENDING_FETCH_LIMIT = 50
KEYWORD_SELECTORS = [
    "div.mZ3RIc",
    "div.enOdEe-wZVHld-aOtOmf div.mZ3RIc",
    "div.feed-item span.title",
    "div.feed-item div.details-header a span",
    "div.feed-item div.title",
]
try:
    PYTRENDS_REQUEST_INTERVAL = max(0.0, float(os.getenv("PYTRENDS_REQUEST_INTERVAL", "300")))
except ValueError:
    PYTRENDS_REQUEST_INTERVAL = 300.0
PYTRENDS_FETCH_DETAILS = os.getenv("PYTRENDS_FETCH_DETAILS", "false").lower() in {"1", "true", "yes"}
TREND_DAILY_API_NS = 15
TREND_DAILY_API_DATE_WINDOW = max(1, int(os.getenv("TREND_DAILY_API_DATE_WINDOW", "3")))


_pytrends_client: Optional[TrendReq] = None
_last_pytrends_request: float = 0.0
_last_collection_strategy: str = "uninitialized"


def _respect_pytrends_rate_limit() -> None:
    """
    pytrends 요청 간 간격을 강제하여 Google 차단을 예방합니다.
    """
    global _last_pytrends_request
    if PYTRENDS_REQUEST_INTERVAL <= 0:
        return

    now = time.monotonic()
    wait_for = (_last_pytrends_request + PYTRENDS_REQUEST_INTERVAL) - now
    if wait_for > 0:
        logger.debug(f"pytrends 요청 간 {wait_for:.2f}s 대기")
        time.sleep(wait_for)
    _last_pytrends_request = time.monotonic()


def _create_webdriver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=ko-KR")
    if headless:
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def _extract_keywords_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    selectors = KEYWORD_SELECTORS
    keywords: List[str] = []
    seen: Set[str] = set()

    for selector in selectors:
        for node in soup.select(selector):
            text = node.get_text(strip=True)
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            keywords.append(text)
    return keywords


def _build_daily_api_param_sets() -> List[Dict[str, Any]]:
    base_dates: List[str] = []
    today = datetime.now(tz=KST)
    for idx in range(TREND_DAILY_API_DATE_WINDOW):
        target = today - timedelta(days=idx)
        base_dates.append(target.strftime("%Y%m%d"))

    base = {"geo": TREND_GEO, "tz": TREND_TZ}
    lang_candidates: List[str] = []
    if TREND_HL:
        lang_candidates.append(TREND_HL)
        lang_root = TREND_HL.split("-", 1)[0]
        if lang_root and lang_root not in lang_candidates:
            lang_candidates.append(lang_root)
    for fallback in ("en-US", "en"):
        if fallback not in lang_candidates:
            lang_candidates.append(fallback)

    param_sets: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for hl in lang_candidates:
        candidate = {**base, "hl": hl}
        for date_str in base_dates:
            dated = {**candidate, "ed": date_str}
            with_ns = {**dated, "ns": TREND_DAILY_API_NS}
            for params in (with_ns, dated):
                key = "&".join(f"{k}={params[k]}" for k in sorted(params))
                if key in seen:
                    continue
                seen.add(key)
                param_sets.append(params)
    return param_sets


def _warmup_http_session(session: requests.Session) -> None:
    warmup_params: List[Dict[str, Any]] = []
    if TREND_HL:
        warmup_params.append({"geo": TREND_GEO, "hl": TREND_HL})
        lang_root = TREND_HL.split("-", 1)[0]
        if lang_root and lang_root != TREND_HL:
            warmup_params.append({"geo": TREND_GEO, "hl": lang_root})
    else:
        warmup_params.append({"geo": TREND_GEO})

    for params in warmup_params:
        try:
            session.get(TREND_DAILY_WARMUP_URL, params=params, timeout=TREND_DAILY_API_TIMEOUT, allow_redirects=True)
            break
        except requests.RequestException as exc:
            logger.debug(f"Google Trends warmup 요청 실패({params}): {exc}")


def _click_load_more(driver: webdriver.Chrome) -> bool:
    try:
        button = driver.find_element(By.CSS_SELECTOR, "div.feed-load-more button")
    except NoSuchElementException:
        button = None
        try:
            button = driver.find_element(By.XPATH, "//button[contains(., '더보기')]")
        except NoSuchElementException:
            pass
        if button is None:
            return _click_next_page(driver)

    if not button.is_enabled():
        return False

    try:
        driver.execute_script("arguments[0].click();", button)
    except WebDriverException:
        return False
    return True


def _collect_keywords_via_selenium(target_count: int, headless: bool = True) -> List[str]:
    driver: Optional[webdriver.Chrome] = None
    keywords: List[str] = []

    try:
        driver = _create_webdriver(headless=headless)
        driver.get(TREND_DAILY_URL)
        _handle_consent_popup(driver)
        wait = WebDriverWait(driver, SELENIUM_WAIT)
        _wait_for_keyword_block(wait)

        attempts = 0
        while len(keywords) < target_count and attempts < 8:
            page_keywords = _extract_keywords_from_html(driver.page_source)
            for kw in page_keywords:
                if kw not in keywords:
                    keywords.append(kw)
                    if len(keywords) >= target_count:
                        break

            if len(keywords) >= target_count:
                break

            if not _click_load_more(driver):
                break

            attempts += 1
            time.sleep(SELENIUM_LOAD_MORE_PAUSE)
    except (TimeoutException, WebDriverException) as exc:
        logger.warning(
            "Selenium 기반 Google Trends 수집 중 오류 (%s): %s",
            exc.__class__.__name__,
            exc,
        )
        _capture_debug_artifacts(driver)
    finally:
        if driver:
            driver.quit()

    return keywords


def _clean_trends_api_payload(raw_text: str) -> str:
    cleaned = raw_text.lstrip(")]}',\n ")
    if not cleaned:
        raise ValueError("일반 텍스트 응답이 비어 있습니다.")
    return cleaned


def _collect_keywords_via_http(target_count: int) -> List[str]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": random.choice(TREND_HTTP_USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": TREND_DAILY_URL,
        }
    )
    _warmup_http_session(session)

    data: Optional[Dict[str, Any]] = None
    for params in _build_daily_api_param_sets():
        try:
            response = session.get(TREND_DAILY_API_URL, params=params, timeout=TREND_DAILY_API_TIMEOUT, allow_redirects=True)
        except requests.RequestException as exc:
            logger.debug(f"HTTP dailytrends 요청 실패({params}): {exc}")
            continue

        if response.status_code == 404:
            logger.debug(f"HTTP dailytrends 404 ({params})")
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.debug(f"HTTP dailytrends 오류({params}): {exc}")
            continue

        try:
            payload = _clean_trends_api_payload(response.text)
            data = json.loads(payload)
            break
        except (ValueError, json.JSONDecodeError) as exc:
            logger.debug(f"dailytrends JSON 파싱 실패({params}): {exc}")
            continue

    if data is None:
        logger.warning("HTTP dailytrends 요청이 모든 파라미터 조합에서 실패했습니다.")
        return []

    keywords: List[str] = []
    seen: Set[str] = set()
    default_section = data.get("default") if isinstance(data, dict) else None
    days = default_section.get("trendingSearchesDays", []) if isinstance(default_section, dict) else []

    for day in days:
        searches = day.get("trendingSearches", []) if isinstance(day, dict) else []
        for entry in searches:
            if not isinstance(entry, dict):
                continue
            keyword = entry.get("title", {}).get("query") if isinstance(entry.get("title"), dict) else None
            if not keyword:
                continue
            normalized = str(keyword).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(normalized)
            if len(keywords) >= target_count:
                logger.info(f"HTTP dailytrends에서 {len(keywords)}개 키워드 확보")
                return keywords

    if keywords:
        logger.info(f"HTTP dailytrends에서 {len(keywords)}개 키워드 확보")
    else:
        logger.warning("HTTP dailytrends에서 키워드를 가져오지 못했습니다.")
    return keywords


def _build_trends_from_keywords(keywords: Sequence[str], count: int, strategy: str) -> List[Dict]:
    if not keywords:
        return []

    client = _get_pytrends_client() if PYTRENDS_FETCH_DETAILS else None
    trends: List[Dict] = []

    for idx, keyword in enumerate(keywords[:count], start=1):
        score = _calc_interest_score(client, keyword) if client else None
        related = expand_related_keywords(keyword) if PYTRENDS_FETCH_DETAILS else []
        if score is None:
            score = max(100 - (idx - 1) * 2, MIN_SCORE)
        trends.append(
            {
                "keyword": keyword,
                "score": score,
                "related": related,
                "collected_at": datetime.now(tz=KST).isoformat(),
            }
        )

    filtered = filter_keywords(trends)
    filtered.sort(key=lambda item: item.get("score", 0), reverse=True)
    if filtered:
        result = filtered[:count]
        logger.info(f"{strategy} 기반 키워드 {len(result)}개 반환")
        global _last_collection_strategy
        _last_collection_strategy = strategy
        return result

    logger.warning(f"{strategy} 기반 키워드가 필터링 조건을 통과하지 못했습니다.")
    return []


def _wait_for_keyword_block(wait: WebDriverWait) -> None:
    last_exc: Optional[Exception] = None
    for selector in KEYWORD_SELECTORS:
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
            return
        except TimeoutException as exc:
            last_exc = exc
    if last_exc:
        raise last_exc


def _click_next_page(driver: webdriver.Chrome) -> bool:
    selectors = [
        "button[aria-label='다음']",
        "button[aria-label*='다음 페이지']",
        "div[role='button'][aria-label='다음']",
    ]
    for selector in selectors:
        try:
            button = driver.find_element(By.CSS_SELECTOR, selector)
        except NoSuchElementException:
            continue
        if not button.is_enabled():
            continue
        try:
            driver.execute_script("arguments[0].click();", button)
            time.sleep(1.5)
            return True
        except WebDriverException:
            continue
    return False


def _handle_consent_popup(driver: webdriver.Chrome) -> None:
    """Google consent 팝업이 있으면 닫습니다."""

    try:
        WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[src*='consent']")))
    except TimeoutException:
        pass
    else:
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//text()[contains(., '동의하고 계속') or contains(., 'I agree')]]"))
            )
            button.click()
        except TimeoutException:
            pass
        finally:
            driver.switch_to.default_content()

    try:
        button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., '동의') or contains(., 'I agree') or contains(., '동의하고 계속')]"))
        )
        button.click()
    except TimeoutException:
        pass


def _capture_debug_artifacts(driver: Optional[webdriver.Chrome]) -> None:
    if not driver:
        return

    debug_dir = PROJECT_ROOT / "logs"
    debug_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=KST).strftime("%Y%m%d_%H%M%S")

    screenshot = debug_dir / f"trends_error_{timestamp}.png"
    html_file = debug_dir / f"trends_error_{timestamp}.html"

    try:
        driver.save_screenshot(str(screenshot))
        logger.info(f"Selenium 디버그 스크린샷 저장: {screenshot}")
    except WebDriverException as exc:
        logger.debug(f"스크린샷 저장 실패: {exc}")

    try:
        html_file.write_text(driver.page_source, encoding="utf-8")
        logger.info(f"Selenium 디버그 HTML 저장: {html_file}")
    except Exception as exc:  # pragma: no cover
        logger.debug(f"HTML 저장 실패: {exc}")


def _get_pytrends_client() -> TrendReq:
    global _pytrends_client
    if _pytrends_client is None:
        _pytrends_client = TrendReq(
            hl=TREND_HL,
            tz=TREND_TZ,
            timeout=(10, 25),
            retries=3,
            backoff_factor=0.2,
        )
    return _pytrends_client


def _gather_seed_keywords(client: TrendReq) -> List[str]:
    """
    trending_searches 한 번만 호출하여 상위 키워드를 확보합니다.
    """
    try:
        _respect_pytrends_rate_limit()
        df = client.trending_searches(pn=TREND_PN)
    except Exception as exc:  # pragma: no cover - network failure guard
        logger.warning(f"트렌드 seed 수집 실패 (trending_searches): {exc}")
        return []

    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.warning("Google Trends trending_searches 결과가 비어 있습니다.")
        return []

    seeds: List[str] = []
    seen: Set[str] = set()
    for raw in df.iloc[:, 0].dropna():
        keyword = str(raw).strip()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        seeds.append(keyword)
        if len(seeds) >= TRENDING_FETCH_LIMIT:
            break

    if seeds:
        logger.info(f"Seed 키워드 {len(seeds)}개 확보 (trending_searches 기준)")
    else:
        logger.warning("Google Trends seed 키워드를 가져오지 못했습니다.")
    return seeds


def _calc_interest_score(client: TrendReq, keyword: str) -> Optional[int]:
    for timeframe in ("now 1-d", "now 7-d", "today 1-m"):
        try:
            _respect_pytrends_rate_limit()
            client.build_payload([keyword], geo=TREND_GEO, timeframe=timeframe)
            _respect_pytrends_rate_limit()
            interest = client.interest_over_time()
        except Exception as exc:  # pragma: no cover - network failure guard
            logger.debug(f"{keyword} interest 수집 실패({timeframe}): {exc}")
            continue

        if isinstance(interest, pd.DataFrame) and not interest.empty:
            series = interest.get(keyword)
            if series is None:
                continue
            score = series.replace(0, pd.NA).dropna().mean()
            if pd.isna(score):
                continue
            return int(round(float(score)))
    return None


def _collect_trends_via_pytrends(count: int) -> List[Dict]:
    client = _get_pytrends_client()
    seeds = _gather_seed_keywords(client)
    if not seeds:
        return []

    trends: List[Dict] = []
    for idx, keyword in enumerate(seeds[:count], start=1):
        score = _calc_interest_score(client, keyword) if PYTRENDS_FETCH_DETAILS else None
        related = expand_related_keywords(keyword) if PYTRENDS_FETCH_DETAILS else []
        if score is None:
            score = max(100 - (idx - 1) * 2, MIN_SCORE)
        trends.append(
            {
                "keyword": keyword,
                "score": score,
                "related": related,
                "collected_at": datetime.now(tz=KST).isoformat(),
            }
        )

    filtered = filter_keywords(trends)
    filtered.sort(key=lambda item: item.get("score", 0), reverse=True)
    return filtered[:count]


def collect_trends(count: int = 50, headless: Optional[bool] = None) -> List[Dict]:
    """
    Google Trends에서 이슈 상품 키워드를 수집합니다.
    
    Args:
        count: 수집할 키워드 개수 (기본값: 50)
        headless: Selenium을 headless 모드로 실행 여부
        
    Returns:
        트렌드 키워드 리스트
        예: [{"keyword": "아이패드", "score": 95, "related": [...]}, ...]
    """
    if headless is None:
        headless = DEFAULT_HEADLESS

    global _last_collection_strategy
    logger.info(f"Google Trends에서 {count}개 키워드 수집 시작")
    pytrends_result = _collect_trends_via_pytrends(count)
    if pytrends_result:
        logger.info(f"pytrends로 {len(pytrends_result)}개 키워드 확보")
        _last_collection_strategy = "pytrends"
        return pytrends_result

    logger.warning("pytrends 수집에 실패하여 HTTP 백업 로직을 실행합니다.")
    http_keywords = _collect_keywords_via_http(count)
    http_result = _build_trends_from_keywords(http_keywords, count, strategy="http_api") if http_keywords else []
    if http_result:
        return http_result

    logger.warning("HTTP 수집 실패로 Selenium 백업 로직을 실행합니다.")
    keywords = _collect_keywords_via_selenium(count, headless=headless)
    if keywords:
        logger.info(f"Selenium으로 {len(keywords)}개 키워드 확보")
    selenium_result = _build_trends_from_keywords(keywords, count, strategy="selenium")
    if selenium_result:
        return selenium_result

    logger.warning("Selenium 수집에서도 키워드를 확보하지 못했습니다.")
    _last_collection_strategy = "failed"
    return []


def expand_related_keywords(keyword: str) -> List[str]:
    """
    키워드의 관련 검색어 및 주제를 확장합니다.
    
    Args:
        keyword: 기준 키워드
        
    Returns:
        관련 키워드 리스트
    """
    if not PYTRENDS_FETCH_DETAILS:
        return []
    logger.info(f"'{keyword}' 관련 키워드 확장")
    client = _get_pytrends_client()
    related: List[str] = []

    try:
        _respect_pytrends_rate_limit()
        client.build_payload([keyword], geo=TREND_GEO, timeframe="now 7-d")
        _respect_pytrends_rate_limit()
        queries = client.related_queries()
        _respect_pytrends_rate_limit()
        topics = client.related_topics()
    except Exception as exc:  # pragma: no cover - network failure guard
        logger.warning(f"관련 키워드 확장 실패 ({keyword}): {exc}")
        return related

    for bucket in ("top", "rising"):
        if queries and keyword in queries:
            df = queries[keyword].get(bucket)
            if isinstance(df, pd.DataFrame):
                related.extend(df.get("query", pd.Series(dtype=str)).dropna().tolist())
        if topics and keyword in topics:
            df = topics[keyword].get(bucket)
            if isinstance(df, pd.DataFrame):
                related.extend(df.get("topic_title", pd.Series(dtype=str)).dropna().tolist())

    normalized_keyword = keyword.strip().lower()
    deduped: List[str] = []
    for item in related:
        if not item:
            continue
        normalized_item = item.strip()
        if not normalized_item:
            continue
        if normalized_item.lower() == normalized_keyword:
            continue
        if normalized_item not in deduped:
            deduped.append(normalized_item)

    return deduped[:10]


def _normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", keyword).strip().lower()


def _looks_like_product(keyword: str) -> bool:
    if not keyword:
        return False
    stripped = keyword.strip()
    if len(stripped) <= 1:
        return False
    if re.search(r"[~!@#$%^&*()\[\]{}<>?/\\|]", stripped):
        return False
    # Too many alphabets only words often news/headline terms
    if stripped.isalpha() and stripped.islower() and len(stripped) > 12:
        return False
    return True


def filter_keywords(keywords: List[Dict]) -> List[Dict]:
    """
    불필요한 키워드를 필터링합니다.
    (연예/정치/뉴스 등 제외)
    
    Args:
        keywords: 필터링할 키워드 리스트
        
    Returns:
        필터링된 키워드 리스트
    """
    logger.info(f"{len(keywords)}개 키워드 필터링 시작")
    filtered: List[Dict] = []
    seen: Set[str] = set()

    for item in keywords:
        keyword = str(item.get("keyword", "")).strip()
        if not keyword:
            continue
        normalized = _normalize_keyword(keyword)
        if not normalized or normalized in seen:
            continue

        score = item.get("score", 0) or 0
        if score < MIN_SCORE:
            continue

        if any(bad in normalized for bad in BAN_KEYWORDS):
            continue

        if not _looks_like_product(keyword):
            continue

        seen.add(normalized)
        filtered.append(item)

    logger.info(f"필터 후 {len(filtered)}개 키워드 남음")
    return filtered


def get_last_collection_strategy() -> str:
    """
    최근 트렌드 수집이 어떤 전략으로 완료되었는지 반환합니다.
    """
    return _last_collection_strategy


def collect_and_store_trends(count: int = 50, headless: Optional[bool] = None, storage: Optional[DataStorage] = None, metadata: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """
    트렌드를 수집하고 저장까지 수행합니다.
    """
    trends = collect_trends(count=count, headless=headless)
    if storage and trends:
        meta = metadata.copy() if metadata else {}
        meta.setdefault("strategy", get_last_collection_strategy())
        try:
            storage.save_trends(trends, metadata=meta)
            logger.info("트렌드 결과를 저장했습니다.")
        except Exception as exc:  # pragma: no cover - IO guard
            logger.error(f"트렌드 저장 실패: {exc}")
    return trends


if __name__ == "__main__":
    keywords = collect_trends()
    for idx, trend in enumerate(keywords, start=1):
        logger.info(
            "[%s] %s (score=%s, related=%s)",
            idx,
            trend.get("keyword"),
            trend.get("score"),
            ", ".join(trend.get("related", [])),
        )
