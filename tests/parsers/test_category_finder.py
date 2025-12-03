"""
카테고리 탐지 테스트 스크립트
단계별로 상세하게 로그를 출력하여 문제를 파악
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import json

from utils.logger import logger
from auto_posting.browser_utils import setup_browser
from ssadagu_parser.crawler import open_ssadagu_menu
from ssadagu_parser.config import BASE_URL


def test_category_detection():
    """
    카테고리 탐지를 단계별로 테스트
    """
    driver = None
    try:
        driver = setup_browser(headless=False)
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 전체카테고리 메뉴 열기
        if not open_ssadagu_menu(driver):
            logger.error("메뉴 열기 실패")
            return
        
        logger.info("=" * 80)
        logger.info("1단계 카테고리 찾기")
        logger.info("=" * 80)
        
        # 1단계 카테고리 찾기
        dep1_links = driver.find_elements(By.CSS_SELECTOR, "ul.dep_1cover.link_cover > li.dep_1 > a.cate_tit")
        logger.info(f"1단계 카테고리: {len(dep1_links)}개 발견")
        
        # 각 1단계 카테고리의 이름 출력
        dep1_names = []
        for i, dep1_link in enumerate(dep1_links, 1):
            name = dep1_link.text.strip()
            dep1_names.append(name)
            logger.info(f"  [{i}] {name}")
        
        logger.info("\n" + "=" * 80)
        logger.info("특정 1단계 카테고리 테스트 (예: '패션의류/이너웨어')")
        logger.info("=" * 80)
        
        # 특정 1단계 카테고리 선택 (예: 패션의류/이너웨어)
        target_dep1_name = "패션의류/이너웨어"
        target_dep1_link = None
        
        for dep1_link in dep1_links:
            if dep1_link.text.strip() == target_dep1_name:
                target_dep1_link = dep1_link
                break
        
        if not target_dep1_link:
            logger.error(f"'{target_dep1_name}' 카테고리를 찾을 수 없습니다")
            return
        
        logger.info(f"\n'{target_dep1_name}'에 hover 시작...")
        
        # 1단계에 hover
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", target_dep1_link
        )
        time.sleep(0.5)
        
        ActionChains(driver).move_to_element(target_dep1_link).perform()
        time.sleep(1.5)
        
        # 2단계 메뉴 찾기 - 중요: 현재 hover한 1단계의 2단계 메뉴만 찾아야 함
        logger.info("\n2단계 메뉴 찾기...")
        
        # 방법 1: 전체 페이지에서 dep_2cover 찾기 (현재 방식)
        dep2_containers_all = driver.find_elements(By.CSS_SELECTOR, "div.dep_2cover")
        logger.info(f"전체 페이지의 dep_2cover 개수: {len(dep2_containers_all)}")
        
        for idx, container in enumerate(dep2_containers_all):
            visible = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).visibility;",
                container
            )
            display = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).display;",
                container
            )
            is_displayed = container.is_displayed()
            
            # 컨테이너 내부의 링크 개수 확인
            links = container.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
            link_texts = [link.text.strip() for link in links if link.text.strip()]
            
            logger.info(f"  dep_2cover[{idx}]: visibility={visible}, display={display}, is_displayed={is_displayed}, 링크={len(link_texts)}개")
            if link_texts:
                logger.info(f"    링크들: {link_texts[:5]}...")  # 처음 5개만
        
        # 방법 2: 현재 hover한 1단계의 부모 li에서 dep_2cover 찾기
        logger.info("\n현재 hover한 1단계의 부모 li에서 dep_2cover 찾기...")
        try:
            dep1_parent = target_dep1_link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_1')]")
            dep2_container_in_parent = dep1_parent.find_element(By.CSS_SELECTOR, "div.dep_2cover")
            
            visible = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).visibility;",
                dep2_container_in_parent
            )
            display = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).display;",
                dep2_container_in_parent
            )
            is_displayed = dep2_container_in_parent.is_displayed()
            
            links = dep2_container_in_parent.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
            link_texts = [link.text.strip() for link in links if link.text.strip()]
            
            logger.info(f"  부모 li 내부 dep_2cover: visibility={visible}, display={display}, is_displayed={is_displayed}, 링크={len(link_texts)}개")
            if link_texts:
                logger.info(f"    링크들: {link_texts}")
        except Exception as e:
            logger.error(f"  부모 li에서 찾기 실패: {e}")
        
        # 2단계 카테고리 링크들 찾기
        logger.info("\n" + "=" * 80)
        logger.info("2단계 카테고리 링크 찾기")
        logger.info("=" * 80)
        
        # 현재 보이는 2단계 링크들 찾기
        dep2_links_all = driver.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
        dep2_links = [link for link in dep2_links_all if link.text.strip()]
        
        logger.info(f"전체 페이지의 dep_2 링크: {len(dep2_links_all)}개")
        logger.info(f"텍스트가 있는 dep_2 링크: {len(dep2_links)}개")
        
        # 각 링크의 텍스트와 부모 확인
        for i, link in enumerate(dep2_links[:10], 1):  # 처음 10개만
            text = link.text.strip()
            try:
                parent = link.find_element(By.XPATH, "./ancestor::li[contains(@class, 'dep_2')]")
                parent_classes = parent.get_attribute("class")
                is_visible = link.is_displayed()
                logger.info(f"  [{i}] '{text}' (parent classes: {parent_classes}, visible: {is_visible})")
            except Exception as e:
                logger.info(f"  [{i}] '{text}' (부모 확인 실패: {e})")
        
        # 잘못된 조합 확인
        logger.info("\n" + "=" * 80)
        logger.info("잘못된 조합 확인 (예: '가전디지털 > 남성의류')")
        logger.info("=" * 80)
        
        # 가전디지털에 hover
        logger.info("\n'가전디지털'에 hover...")
        gaepon_link = None
        for dep1_link in dep1_links:
            if dep1_link.text.strip() == "가전디지털":
                gaepon_link = dep1_link
                break
        
        if gaepon_link:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", gaepon_link
            )
            time.sleep(0.5)
            ActionChains(driver).move_to_element(gaepon_link).perform()
            time.sleep(1.5)
            
            # 가전디지털의 2단계 링크들 찾기
            dep2_links_gaepon = driver.find_elements(By.CSS_SELECTOR, "li.dep_2 > a.cate_tit")
            dep2_texts_gaepon = [link.text.strip() for link in dep2_links_gaepon if link.text.strip()]
            
            logger.info(f"가전디지털의 2단계 카테고리: {len(dep2_texts_gaepon)}개")
            logger.info(f"  링크들: {dep2_texts_gaepon}")
            
            # "남성의류"가 있는지 확인
            if "남성의류" in dep2_texts_gaepon:
                logger.error("  ❌ 문제 발견! '가전디지털' 하위에 '남성의류'가 있습니다!")
            else:
                logger.info("  ✓ '가전디지털' 하위에 '남성의류'는 없습니다 (정상)")
        
        # 브라우저를 열어둬서 확인할 수 있게
        logger.info("\n" + "=" * 80)
        logger.info("테스트 완료. 브라우저를 10초간 열어둡니다...")
        logger.info("=" * 80)
        time.sleep(10)
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            input("브라우저를 닫으려면 Enter를 누르세요...")
            driver.quit()
            logger.info("브라우저 종료")


if __name__ == "__main__":
    test_category_detection()


