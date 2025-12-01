import logging
import time
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class Actions:
    """카테고리 선택 등 UI 제스처를 wrapping하는 helper."""

    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def wait_visible(self, xpath):
        return self.wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))

    def js_click(self, element):
        for _ in range(3):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", element
                )
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", element)
                return
            except Exception:
                time.sleep(0.2)
                continue
        raise

    def wait_radix_open(self, trigger):
        """방금 클릭한 trigger가 제어하는 dropdown 컨테이너가 열릴 때까지 대기."""
        menu_id = trigger.get_attribute("aria-controls") or trigger.get_attribute(
            "data-controls"
        )
        if menu_id:
            locator = (
                By.XPATH,
                f"//div[@id='{menu_id}' and @data-state='open']",
            )
        else:
            locator = (By.XPATH, "//div[@data-state='open']")

        self.wait.until(EC.visibility_of_element_located(locator))
        return menu_id

    def select_category(self, label, category_name):
        """주어진 라벨의 카테고리 드롭다운에서 원하는 항목을 선택한다."""
        logging.info(f"카테고리 '{label}' 선택 → {category_name}")

        btn_xpath = f"//button[./span[text()='{label}']]"
        last_error = None

        for attempt in range(3):
            try:
                dropdown_btn = self.wait_visible(btn_xpath)
                self.js_click(dropdown_btn)

                menu_id = self.wait_radix_open(dropdown_btn)
                time.sleep(0.1)  # Radix 애니메이션 안정화

                if menu_id:
                    option_xpath = (
                        f"//div[@id='{menu_id}' and @data-state='open']"
                        f"//span[text()='{category_name}']"
                    )
                else:
                    option_xpath = (
                        f"//div[@data-state='open']//span[text()='{category_name}']"
                    )

                option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, option_xpath))
                )
                self.js_click(option)

                logging.info(f"{label} 선택 완료")
                return

            except (
                StaleElementReferenceException,
                TimeoutException,
                WebDriverException,
            ) as exc:
                last_error = exc
                logging.debug(
                    "카테고리 '%s' 선택 재시도 (%d/3): %s", label, attempt + 1, exc
                )
                time.sleep(0.5)

        raise last_error or RuntimeError(f"카테고리 '{label}' 선택 실패")
