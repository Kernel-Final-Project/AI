import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc

class DriverFactory:
    """설정 가능한 옵션으로 Chrome WebDriver를 생성한다."""

    def __init__(
        self,
        headless: bool = False,
        driver_path: str | Path | None = None,
        cache_dir: str | Path | None = None,
    ):
        self.headless = headless
        self.driver_path = Path(driver_path) if driver_path else None
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "chromedriver"

    def create(self):
        """옵션을 구성하고 WebDriver 인스턴스를 반환한다."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")

        options.add_argument('--disable-blink-features=AutomationControlled')
        # Chrome 143+에서는 excludeSwitches/useAutomationExtension 옵션이 거부되므로 제거
        if self.headless:
            options.add_argument("--headless=new")

        logging.info("Chrome WebDriver 시작중...")

        if self.driver_path and self.driver_path.is_file():
            service = Service(str(self.driver_path))
        else:
            manager = ChromeDriverManager()
            cached_driver_path = manager.install()
            service = Service(cached_driver_path)

        driver = uc.Chrome(options=options, use_subprocess=True)
        return driver
