import argparse
import logging
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait

from keywordCrawler.infra.driver_factory import DriverFactory
from keywordCrawler.infra.extractors import KeywordExtractor
from keywordCrawler.infra.selenium_actions import Actions
from keywordCrawler.repositories.csv_repository import CSVKeywordRepository
from keywordCrawler.services.category_service import CategoryService, crawl_keywords_to_list

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "keywords.csv"


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Itemscout 인기 키워드 크롤러",
    )
    parser.add_argument("--c1", required=True, help="1차 카테고리")
    parser.add_argument("--c2", help="2차 카테고리")
    parser.add_argument("--c3", help="3차 카테고리")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"저장할 CSV 파일 경로 (기본: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="브라우저를 headless 모드로 실행",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=15,
        help="명시적 대기 타임아웃 (초)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="카테고리 선택 사이의 지연 시간 (초)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="로그 레벨",
    )

    return parser.parse_args(args=args)


def crawl_keywords(
    c1: str,
    c2: str | None = None,
    c3: str | None = None,
    *,
    output_path: Path | None = None,
    headless: bool = False,
    wait_timeout: int = 15,
    delay: float = 0.3,
) -> list[str]:
    """Selenium을 이용해 키워드를 추출한 뒤 CSV에 저장하고 리스트를 반환한다."""
    repository = CSVKeywordRepository(default_path=output_path or DEFAULT_OUTPUT_PATH)
    driver = None
    try:
        factory = DriverFactory(headless=headless)
        driver = factory.create()

        wait = WebDriverWait(driver, wait_timeout)
        actions = Actions(driver, wait)
        extractor = KeywordExtractor(driver, wait)
        service = CategoryService(
            driver,
            wait,
            actions,
            extractor,
            repository=repository,
            delay=delay,
        )
        categories = (c1, c2, c3)
        return service.crawl(categories, output_path=repository.default_path)
    finally:
        if driver:
            driver.quit()


def main_cli(args=None):
    cli_args = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, cli_args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 실제 크롤링은 서비스 함수로 위임
    keywords = crawl_keywords_to_list(
        cli_args.c1,
        cli_args.c2,
        cli_args.c3,
        output_path=cli_args.output,
        headless=cli_args.headless,
        wait_timeout=cli_args.wait_timeout,
        delay=cli_args.delay,
    )
    print("키워드:", keywords)
    return 0
