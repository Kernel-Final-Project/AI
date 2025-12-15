"""
크롤링 서비스 모듈
기존 크롤링 함수들을 래핑하여 API에서 사용할 수 있도록 함
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import traceback

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.logger import logger


class CrawlerService:
    """크롤링 서비스 클래스"""
    
    def __init__(self):
        self.project_root = project_root
    
    def crawl_musinsa(
        self,
        max_products_per_category: int = 10,
        categories: Optional[List[str]] = None
    ) -> Dict:
        """
        무신사 크롤링 실행
        
        Args:
            max_products_per_category: 카테고리당 최대 상품 수
            categories: 특정 카테고리만 크롤링 (None이면 전체)
            
        Returns:
            크롤링 결과 딕셔너리
        """
        try:
            logger.info(f"무신사 크롤링 시작: max_products={max_products_per_category}")
            
            # 무신사 크롤링 모듈 import
            from auto_posting.browser_utils import setup_browser
            from musinsa_parser.category_crawler import (
                build_top_categories,
                click_1depth_and_get_2depth,
                navigate_to_2depth_category
            )
            from musinsa_parser.product_crawler import extract_products_xpath
            from musinsa_parser.category_node import CategoryNode
            from datetime import datetime
            
            driver = None
            all_results = {}
            total_crawled = 0
            
            try:
                driver = setup_browser(headless=True)
                
                # 1depth 카테고리 가져오기
                top_categories = build_top_categories(driver)
                
                if not top_categories:
                    logger.warning("1depth 카테고리를 찾을 수 없습니다")
                    return {"categories": {}, "total_products": 0}
                
                # 2depth 카테고리 탐색 및 크롤링
                for _1depth_node in top_categories:
                    # depth가 1이 아닌 경우 건너뛰기
                    if _1depth_node.depth != 1:
                        continue
                    
                    _1depth_name = _1depth_node.name
                    
                    if categories and _1depth_name not in categories:
                        continue
                    
                    # 2depth 카테고리 가져오기 (category_id 전달)
                    _2depth_list = click_1depth_and_get_2depth(driver, _1depth_node.category_id)
                    
                    for _2depth_node in _2depth_list:
                        _2depth_name = _2depth_node.name
                        _2depth_url = _2depth_node.url
                        category_path_str = f"{_1depth_name} > {_2depth_name}"
                        
                        if categories and category_path_str not in categories:
                            continue
                        
                        try:
                            logger.info(f"크롤링 중: {category_path_str}")
                            
                            # 2depth 카테고리로 이동
                            navigate_to_2depth_category(driver, _2depth_url)
                            
                            # 상품 추출
                            products = extract_products_xpath(driver, limit=max_products_per_category)
                            
                            if products:
                                all_results[category_path_str] = {
                                    "category_path": [_1depth_name, _2depth_name],
                                    "category_url": _2depth_url,
                                    "product_count": len(products),
                                    "products": products
                                }
                                total_crawled += len(products)
                            else:
                                all_results[category_path_str] = {
                                    "category_path": [_1depth_name, _2depth_name],
                                    "category_url": _2depth_url,
                                    "product_count": 0,
                                    "products": []
                                }
                                
                        except Exception as e:
                            logger.error(f"카테고리 크롤링 실패 ({category_path_str}): {e}")
                            all_results[category_path_str] = {
                                "category_path": [_1depth_name, _2depth_name],
                                "category_url": _2depth_url,
                                "product_count": 0,
                                "products": []
                            }
                
                result = {
                    "crawl_date": datetime.now().isoformat(),
                    "total_categories": len(all_results),
                    "total_products": total_crawled,
                    "categories": all_results
                }
                
                logger.info(f"무신사 크롤링 완료: {total_crawled}개 상품")
                return result
                
            finally:
                if driver:
                    driver.quit()
                    logger.info("브라우저 종료")
                    
        except Exception as e:
            logger.error(f"무신사 크롤링 중 오류 발생: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def crawl_ssadagu(
        self,
        max_products_per_category: int = 10,
        categories: Optional[List[str]] = None
    ) -> Dict:
        """
        싸다구 크롤링 실행
        
        Args:
            max_products_per_category: 카테고리당 최대 상품 수
            categories: 특정 카테고리만 크롤링 (None이면 전체)
            
        Returns:
            크롤링 결과 딕셔너리
        """
        try:
            logger.info(f"싸다구 크롤링 시작: max_products={max_products_per_category}")
            
            from auto_posting.browser_utils import setup_browser
            from ssadagu_parser.category_finder import find_all_category_paths
            from ssadagu_parser.crawler import crawl_from_main, navigate_to_category, _crawl_category_page
            from datetime import datetime
            
            driver = None
            all_results = {}
            total_crawled = 0
            
            try:
                # 브라우저 한 번만 생성
                driver = setup_browser(headless=True)
                logger.info("브라우저 시작 (모든 카테고리 재사용)")
                
                # 카테고리 경로 탐지
                category_paths = find_all_category_paths()
                
                if not category_paths:
                    logger.warning("카테고리 경로를 찾을 수 없습니다")
                    return {"categories": {}, "total_products": 0}
                
                # 모든 카테고리에 대해 같은 브라우저 재사용
                for category_path in category_paths:
                    category_str = " > ".join(category_path)
                    
                    if categories and category_str not in categories:
                        continue
                    
                    try:
                        logger.info(f"크롤링 중: {category_str}")
                        
                        # 같은 브라우저 인스턴스를 전달하여 재사용
                        products = crawl_from_main(
                            category_path, 
                            max_products=max_products_per_category,
                            driver=driver
                        )
                        
                        category_key = " > ".join(category_path)
                        
                        if products:
                            all_results[category_key] = {
                                "category_path": category_path,
                                "product_count": len(products),
                                "products": products
                            }
                            total_crawled += len(products)
                        else:
                            all_results[category_key] = {
                                "category_path": category_path,
                                "product_count": 0,
                                "products": []
                            }
                            
                    except Exception as e:
                        logger.error(f"카테고리 크롤링 실패 ({category_str}): {e}")
                        category_key = " > ".join(category_path)
                        all_results[category_key] = {
                            "category_path": category_path,
                            "product_count": 0,
                            "products": []
                        }
                
                result = {
                    "crawl_date": datetime.now().isoformat(),
                    "total_categories": len(all_results),
                    "total_products": total_crawled,
                    "categories": all_results
                }
                
                logger.info(f"싸다구 크롤링 완료: {total_crawled}개 상품")
                return result
                
            finally:
                # 모든 카테고리 크롤링 완료 후 브라우저 종료
                if driver:
                    driver.quit()
                    logger.info("브라우저 종료")
                    
        except Exception as e:
            logger.error(f"싸다구 크롤링 중 오류 발생: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def crawl_gmarket(
        self,
        max_products_per_category: int = 10,
        categories: Optional[List[str]] = None
    ) -> Dict:
        """
        지마켓 크롤링 실행 (실시간 크롤링)
        
        Args:
            max_products_per_category: 카테고리당 최대 상품 수
            categories: 특정 카테고리만 크롤링 (None이면 전체)
            
        Returns:
            크롤링 결과 딕셔너리
        """
        try:
            logger.info(f"지마켓 크롤링 시작: max_products={max_products_per_category}")
            
            # 지마켓 크롤링 모듈 import
            import sys
            from pathlib import Path
            from datetime import datetime
            
            # gmarket 디렉토리를 Python 경로에 추가
            gmarket_dir = self.project_root / "gmarket"
            if str(gmarket_dir) not in sys.path:
                sys.path.insert(0, str(gmarket_dir))
            
            from gmarket_crawl import main as gmarket_main, CATEGORY_PATHS
            
            # 카테고리 경로 필터링 (categories가 지정된 경우)
            category_paths = CATEGORY_PATHS
            if categories:
                # categories는 "level1 > level2" 형식일 것으로 예상
                filtered_paths = []
                for path in CATEGORY_PATHS:
                    if len(path) >= 2:
                        category_key = f"{path[0]} > {path[1]}"
                        if category_key in categories:
                            filtered_paths.append(path)
                category_paths = filtered_paths if filtered_paths else CATEGORY_PATHS
            
            logger.info(f"크롤링할 카테고리 경로: {len(category_paths)}개")
            
            # 크롤링 실행 (headless=False로 설정하여 브라우저 창 표시)
            products_data = gmarket_main(
                headless=False,
                max_items_per_leaf=max_products_per_category,
                category_paths=category_paths
            )
            
            if not products_data:
                logger.warning("크롤링된 상품이 없습니다")
                return {"categories": {}, "total_products": 0}
            
            # 카테고리별로 그룹화
            categories_dict = {}
            total_products = 0
            
            for product in products_data:
                level1 = product.get("level1_name", "")
                level2 = product.get("level2_name", "")
                level3 = product.get("level3_name", "")
                
                category_key = f"{level1} > {level2} > {level3}"
                
                if category_key not in categories_dict:
                    categories_dict[category_key] = {
                        "category_path": [level1, level2, level3],
                        "product_count": 0,
                        "products": []
                    }
                
                categories_dict[category_key]["products"].append(product)
                categories_dict[category_key]["product_count"] += 1
                total_products += 1
            
            result = {
                "crawl_date": datetime.now().isoformat(),
                "total_categories": len(categories_dict),
                "total_products": total_products,
                "categories": categories_dict
            }
            
            logger.info(f"지마켓 크롤링 완료: {total_products}개 상품")
            return result
            
        except Exception as e:
            logger.error(f"지마켓 크롤링 중 오류 발생: {e}")
            logger.error(traceback.format_exc())
            raise
