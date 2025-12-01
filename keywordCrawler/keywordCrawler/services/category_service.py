import logging
import time
from selenium.webdriver.support.ui import WebDriverWait


class CategoryService:
    """카테고리 선택부터 키워드 추출/저장까지 전체 흐름을 관리한다."""

    CATEGORY_LABELS = ("1차 카테고리", "2차 카테고리", "3차 카테고리")
    URL = "https://itemscout.io/category"

    def __init__(
        self,
        driver,
        wait: WebDriverWait,
        actions,
        extractor,
        repository=None,
        delay=0.3,
    ):
        self.driver = driver
        self.wait = wait
        self.actions = actions
        self.extractor = extractor
        self.repository = repository
        self.delay = delay

    def category_flow(self, categories):
        """선택된 카테고리 레벨에 맞춰 순차적으로 드롭다운을 조작한다."""
        for label, value in zip(self.CATEGORY_LABELS, categories):
            if not value:
                logging.debug("카테고리 '%s' 값이 없어 선택 중단", label)
                break

            max_attempts = 3 if self.extractor else 1

            for attempt in range(1, max_attempts + 1):
                if self.extractor:
                    self.extractor.mark_for_refresh()

                self.actions.select_category(label, value)
                time.sleep(self.delay)

                if not self.extractor:
                    break

                if self.extractor.wait_for_refresh():
                    break

                logging.debug(
                    "카테고리 '%s' 키워드 갱신 미확인, 재시도 (%d/%d)",
                    label,
                    attempt,
                    max_attempts,
                )
                time.sleep(self.delay)
            else:
                logging.warning(
                    "카테고리 '%s' 선택 후 키워드 갱신을 감지하지 못했습니다.", label
                )

    def crawl(self, categories, output_path=None):
        """카테고리 페이지에 접속해 키워드를 추출하고 저장한다."""
        if not categories or not categories[0]:
            raise ValueError("최소한 1차 카테고리는 지정해야 합니다.")

        logging.info("Itemscout 페이지 접속")
        self.driver.get(self.URL)

        self.category_flow(categories)
        keywords = self.extractor.extract_keywords()

        if keywords and self.repository:
            self.repository.save(keywords, output_path=output_path)

        return keywords
