import logging
import time
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class KeywordExtractor:
    """카테고리 페이지에서 인기 키워드 목록을 추출한다."""

    def __init__(
        self,
        driver,
        wait,
        settle_timeout=5.0,
        settle_interval=0.5,
        selectors=None,
    ):
        self.driver = driver
        self.wait = wait
        base_selectors = selectors or [
            "span[class*='KeywordMetaCell_keyword-label']",
            "span.KeywordMetaCell_keyword-label__r0p9W",
        ]
        self.selector = ", ".join(base_selectors)
        self._anchor_element = None
        self._anchor_text = None
        self.settle_timeout = settle_timeout
        self.settle_interval = settle_interval

    def mark_for_refresh(self):
        """현재 키워드 첫 요소를 anchor로 저장해 다음 갱신을 감지한다."""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, self.selector)
            if elements:
                self._anchor_element = elements[0]
                self._anchor_text = (self._anchor_element.text or "").strip()
            else:
                self._anchor_element = None
                self._anchor_text = None
        except Exception:
            self._anchor_element = None
            self._anchor_text = None

    def wait_for_refresh(self):
        """anchor가 교체될 때까지 기다린 뒤 새로운 키워드가 보일 때까지 대기."""
        anchor_text = self._anchor_text
        anchor_exists = bool(self._anchor_element or anchor_text)
        refreshed = not anchor_exists

        if self._anchor_element:
            try:
                self.wait.until(EC.staleness_of(self._anchor_element))
                refreshed = True
            except TimeoutException:
                logging.debug("키워드 목록 staleness 대기 시간 초과, 계속 진행합니다.")

        if not refreshed and anchor_text:
            try:

                def text_changed(driver):
                    elements = driver.find_elements(By.CSS_SELECTOR, self.selector)
                    if not elements:
                        return False
                    current_text = (elements[0].text or "").strip()
                    return current_text and current_text != anchor_text

                self.wait.until(text_changed)
                refreshed = True
            except TimeoutException:
                logging.debug("키워드 텍스트 변경 대기 시간 초과, 계속 진행합니다.")

        try:
            self.wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, self.selector))
            )
        except TimeoutException:
            logging.warning("키워드 요소가 나타나지 않았습니다.")
        finally:
            self._anchor_element = None
            self._anchor_text = None

        return refreshed

    def _read_keywords(self):
        script = (
            "return Array.from(document.querySelectorAll(arguments[0]))"
            ".map(el => el.textContent.trim()).filter(Boolean);"
        )
        return self.driver.execute_script(script, self.selector)

    def extract_keywords(self):
        """키워드 목록이 안정될 때까지 polling한 뒤 텍스트 리스트 반환."""
        last_snapshot = None
        stable_snapshot = None
        consecutive_same = 0
        deadline = time.monotonic() + self.settle_timeout

        while True:
            try:
                self.wait.until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, self.selector))
                )
                keywords = self._read_keywords()
            except StaleElementReferenceException as exc:
                logging.debug("키워드 요소 stale 발생, 재시도: %s", exc)
                time.sleep(self.settle_interval)
                continue
            except TimeoutException as exc:
                logging.error(f"키워드 로딩 시간 초과: {exc}")
                break
            except Exception as exc:
                logging.error(f"키워드 추출 실패: {exc}")
                break

            if keywords:
                if keywords == last_snapshot:
                    consecutive_same += 1
                else:
                    consecutive_same = 0
                    deadline = time.monotonic() + self.settle_timeout

                last_snapshot = keywords
                stable_snapshot = keywords

                if consecutive_same >= 1:
                    logging.info(f"키워드 {len(keywords)}개 추출됨")
                    return keywords
            else:
                logging.warning("키워드 요소를 찾았지만 텍스트가 비어 있습니다.")

            if time.monotonic() >= deadline:
                if stable_snapshot:
                    logging.info(
                        "키워드 안정화 대기 시간 초과, 마지막 스냅샷 %d개 반환",
                        len(stable_snapshot),
                    )
                else:
                    logging.warning("키워드 정보를 얻지 못했습니다.")
                return stable_snapshot or last_snapshot or []

            time.sleep(self.settle_interval)
