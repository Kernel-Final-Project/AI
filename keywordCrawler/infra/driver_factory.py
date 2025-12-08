import logging
import tempfile
import shutil
import atexit
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class DriverFactory:
    """설정 가능한 옵션으로 Chrome WebDriver를 생성한다."""

    def __init__(
        self,
        headless: bool = False,
        driver_path: str | Path | None = None,
        cache_dir: str | Path | None = None,
        profile_dir: str | Path | None = None,
        use_temp_profile: bool = True,
    ):
        self.headless = headless
        self.driver_path = Path(driver_path) if driver_path else None
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "chromedriver"
        self.profile_dir = Path(profile_dir) if profile_dir else None
        self.use_temp_profile = use_temp_profile
        self._created_profile_dir: Path | None = None

    def create(self):
        """옵션을 구성하고 WebDriver 인스턴스를 반환한다."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        if self.headless:
            options.add_argument("--headless=new")

        profile_dir = self.profile_dir
        if not profile_dir and self.use_temp_profile:
            # 저장소 루트에 흔적을 남기지 않도록 OS 임시 디렉터리에 프로필 생성
            self._created_profile_dir = Path(tempfile.mkdtemp(prefix="chromedriver-profile-"))
            profile_dir = self._created_profile_dir
            atexit.register(shutil.rmtree, profile_dir, ignore_errors=True)

        if profile_dir:
            profile_dir.mkdir(parents=True, exist_ok=True)
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument(f"--disk-cache-dir={profile_dir / 'cache'}")

        logging.info("Chrome WebDriver 시작중...")

        if self.driver_path and self.driver_path.is_file():
            service = Service(str(self.driver_path))
        else:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            manager = ChromeDriverManager(path=str(self.cache_dir))
            cached_driver_path = manager.install()
            service = Service(cached_driver_path)

        driver = webdriver.Chrome(service=service, options=options)
        return driver
