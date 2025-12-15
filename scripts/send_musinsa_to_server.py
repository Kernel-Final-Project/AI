"""
무신사/싸다구/지마켓 크롤링 결과를 Spring 서버로 전송하는 스크립트
"""
import json
import os
import sys
import argparse
from typing import List, Dict, Optional, Union
import requests
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logger import logger


def detect_site_type(json_data: Dict, file_path: str = "") -> str:
    """
    JSON 데이터나 파일 경로로부터 사이트 타입 감지
    
    Args:
        json_data: JSON 데이터
        file_path: 파일 경로 (선택적)
        
    Returns:
        "musinsa", "ssadagu", 또는 "gmarket"
    """
    # 파일 경로로 감지
    if file_path:
        file_path_lower = file_path.lower()
        if "musinsa" in file_path_lower:
            return "musinsa"
        elif "ssadagu" in file_path_lower:
            return "ssadagu"
        elif "gmarket" in file_path_lower:
            return "gmarket"
    
    # JSON 구조로 감지
    # 지마켓: 배열 형태 (리스트)
    if isinstance(json_data, list):
        # 배열의 첫 번째 요소에 level1_name, level2_name 등이 있으면 지마켓
        if json_data and isinstance(json_data[0], dict):
            if "level1_name" in json_data[0] and "product_code" in json_data[0]:
                return "gmarket"
    
    # 무신사: categories 안에 category_url이 있음
    # 싸다구: categories 안에 category_path가 있음
    categories = json_data.get("categories", {})
    if categories:
        first_category = list(categories.values())[0]
        if "category_url" in first_category:
            return "musinsa"
        elif "category_path" in first_category:
            return "ssadagu"
    
    # 기본값은 무신사 (하위 호환성)
    return "musinsa"


def extract_products_musinsa(json_data: Dict) -> List[Dict]:
    """
    무신사 JSON 데이터에서 상품 정보를 추출하여 평탄화된 리스트로 변환
    
    Args:
        json_data: 크롤링 결과 JSON 데이터
        
    Returns:
        상품 정보 리스트 (각 상품에 site_name, site_url 추가됨)
    """
    result = []
    
    try:
        categories = json_data.get("categories", {})
        
        if not categories:
            logger.warning("categories 키가 없거나 비어있습니다")
            return result
        
        for category_name, category_info in categories.items():
            products = category_info.get("products", [])
            
            if not products:
                logger.debug(f"카테고리 '{category_name}'에 상품이 없습니다")
                continue
            
            category_url = category_info.get("category_url", "")
            
            for p in products:
                # product_price는 서버에서 String으로 받아서 파싱하므로 원본 문자열 유지
                raw_price = p.get("product_price", "")
                product_price = raw_price if raw_price and raw_price != "N/A" else ""
                
                # 서버 DTO가 @JsonProperty로 snake_case를 기대함
                product_data = {
                    "site_name": "musinsa",
                    "site_url": category_url,
                    "product_name": p.get("product_name"),
                    "product_code": p.get("product_code"),
                    "product_detail_url": p.get("product_url"),  # 서버 필수 필드
                    "product_price": product_price,  # String으로 전송 (서버에서 파싱)
                    "image_url": p.get("image_url")
                }
                
                # 필수 필드 검증
                if product_data["product_code"] and product_data["product_name"] and product_data["product_detail_url"]:
                    result.append(product_data)
                else:
                    logger.warning(f"필수 필드 누락된 상품 건너뜀: {product_data}")
        
        logger.info(f"총 {len(result)}개 상품 추출 완료 (무신사)")
        return result
        
    except Exception as e:
        logger.error(f"상품 추출 중 오류 발생: {e}")
        raise


def extract_products_ssadagu(json_data: Dict) -> List[Dict]:
    """
    싸다구 JSON 데이터에서 상품 정보를 추출하여 평탄화된 리스트로 변환
    
    Args:
        json_data: 크롤링 결과 JSON 데이터
        
    Returns:
        상품 정보 리스트 (각 상품에 site_name, site_url 추가됨)
    """
    result = []
    
    try:
        categories = json_data.get("categories", {})
        
        if not categories:
            logger.warning("categories 키가 없거나 비어있습니다")
            return result
        
        for category_name, category_info in categories.items():
            products = category_info.get("products", [])
            
            if not products:
                logger.debug(f"카테고리 '{category_name}'에 상품이 없습니다")
                continue
            
            # 싸다구는 category_url이 없으므로 기본 URL 사용
            category_url = "https://ssadagu.kr"
            
            for p in products:
                # 싸다구 상품 필드: title, price, image_url, product_url, product_id
                # 무신사와 매핑: title -> product_name, product_id -> product_code
                raw_price = p.get("price", "")
                product_price = raw_price if raw_price and raw_price != "N/A" else ""
                
                # product_id를 product_code로 매핑
                product_code = p.get("product_id", "")
                
                # 서버 DTO가 @JsonProperty로 snake_case를 기대함
                product_data = {
                    "site_name": "ssadagu",
                    "site_url": category_url,
                    "product_name": p.get("title"),
                    "product_code": product_code,
                    "product_detail_url": p.get("product_url"),  # 서버 필수 필드
                    "product_price": product_price,  # String으로 전송 (서버에서 파싱)
                    "image_url": p.get("image_url", "")
                }
                
                # 필수 필드 검증
                if product_data["product_code"] and product_data["product_name"] and product_data["product_detail_url"]:
                    result.append(product_data)
                else:
                    logger.warning(f"필수 필드 누락된 상품 건너뜀: {product_data}")
        
        logger.info(f"총 {len(result)}개 상품 추출 완료 (싸다구)")
        return result
        
    except Exception as e:
        logger.error(f"상품 추출 중 오류 발생: {e}")
        raise


def extract_products_gmarket(json_data: Union[List[Dict], Dict]) -> List[Dict]:
    """
    지마켓 JSON 데이터에서 상품 정보를 추출하여 평탄화된 리스트로 변환
    
    Args:
        json_data: 크롤링 결과 JSON 데이터 (배열 형태)
        
    Returns:
        상품 정보 리스트 (각 상품에 site_name, site_url 추가됨)
    """
    result = []
    
    try:
        if not isinstance(json_data, list):
            logger.warning("지마켓 데이터는 배열 형태여야 합니다")
            return result
        
        if not json_data:
            logger.warning("지마켓 데이터가 비어있습니다")
            return result
        
        site_url = "https://www.gmarket.co.kr"
        
        for p in json_data:
            # 지마켓 상품 필드: product_code, product_name, product_price, image_url, product_url
            # level1_name, level2_name, level3_name은 카테고리 정보 (선택적)
            raw_price = p.get("product_price", "")
            product_price = raw_price if raw_price and raw_price != "N/A" else ""
            
            # 서버 DTO가 @JsonProperty로 snake_case를 기대함
            product_data = {
                "site_name": "gmarket",
                "site_url": site_url,
                "product_name": p.get("product_name"),
                "product_code": p.get("product_code"),
                "product_detail_url": p.get("product_url"),  # 서버 필수 필드
                "product_price": product_price,  # String으로 전송 (서버에서 파싱)
                "image_url": p.get("image_url", "")
            }
            
            # 필수 필드 검증
            if product_data["product_code"] and product_data["product_name"] and product_data["product_detail_url"]:
                result.append(product_data)
            else:
                logger.warning(f"필수 필드 누락된 상품 건너뜀: {product_data}")
        
        logger.info(f"총 {len(result)}개 상품 추출 완료 (지마켓)")
        return result
        
    except Exception as e:
        logger.error(f"지마켓 상품 추출 중 오류 발생: {e}")
        raise


def extract_products(json_data: Union[Dict, List[Dict]], site_type: str = "auto", file_path: str = "") -> List[Dict]:
    """
    JSON 데이터에서 상품 정보를 추출 (사이트 타입 자동 감지)
    
    Args:
        json_data: 크롤링 결과 JSON 데이터 (딕셔너리 또는 리스트)
        site_type: "musinsa", "ssadagu", "gmarket", 또는 "auto" (자동 감지)
        file_path: 파일 경로 (자동 감지용)
        
    Returns:
        상품 정보 리스트
    """
    if site_type == "auto":
        site_type = detect_site_type(json_data, file_path)
        logger.info(f"사이트 타입 자동 감지: {site_type}")
    
    if site_type == "musinsa":
        return extract_products_musinsa(json_data)
    elif site_type == "ssadagu":
        return extract_products_ssadagu(json_data)
    elif site_type == "gmarket":
        return extract_products_gmarket(json_data)
    else:
        raise ValueError(f"지원하지 않는 사이트 타입: {site_type}")


def send_to_server(
    products_list: List[Dict],
    server_url: str = "http://localhost:8080/api/v1/crawling/products",
    batch_size: Optional[int] = None,
    timeout: int = 30
) -> bool:
    """
    상품 리스트를 Spring 서버로 전송
    
    Args:
        products_list: 전송할 상품 리스트
        server_url: Spring 서버 API 엔드포인트 URL
        batch_size: 배치 크기 (None이면 전체 한 번에 전송)
        timeout: 요청 타임아웃 (초)
        
    Returns:
        전송 성공 여부
    """
    if not products_list:
        logger.warning("전송할 상품이 없습니다")
        return False
    
    try:
        if batch_size and batch_size > 0:
            # 배치 처리
            total_batches = (len(products_list) + batch_size - 1) // batch_size
            success_count = 0
            
            logger.info(f"배치 전송 시작: 총 {len(products_list)}개 상품, {total_batches}개 배치")
            
            for i in range(0, len(products_list), batch_size):
                batch = products_list[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"[{batch_num}/{total_batches}] 배치 전송 중... ({len(batch)}개 상품)")
                
                # 디버깅: 첫 번째 배치의 실제 전송 데이터 로깅
                if batch_num == 1:
                    logger.debug(f"전송 데이터 샘플: {json.dumps(batch[0] if batch else {}, ensure_ascii=False, indent=2)}")
                
                response = requests.post(
                    server_url,
                    json=batch,
                    timeout=timeout
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(f"[{batch_num}/{total_batches}] 배치 전송 성공")
                    success_count += 1
                else:
                    logger.error(
                        f"[{batch_num}/{total_batches}] 배치 전송 실패: "
                        f"상태 코드 {response.status_code}, 응답: {response.text[:200]}"
                    )
            
            if success_count == total_batches:
                logger.info(f"✅ 전체 배치 전송 완료: {success_count}/{total_batches}")
                return True
            else:
                logger.warning(f"⚠️  일부 배치 전송 실패: {success_count}/{total_batches}")
                return False
        else:
            # 전체 한 번에 전송
            logger.info(f"전체 상품 전송 시작: {len(products_list)}개")
            
            # 디버깅: 첫 번째 상품의 실제 전송 데이터 로깅
            if products_list:
                logger.debug(f"전송 데이터 샘플: {json.dumps(products_list[0], ensure_ascii=False, indent=2)}")
            
            response = requests.post(
                server_url,
                json=products_list,
                timeout=timeout
            )
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"✅ 전체 상품 전송 성공: {len(products_list)}개")
                return True
            else:
                logger.error(
                    f"❌ 상품 전송 실패: 상태 코드 {response.status_code}, "
                    f"응답: {response.text[:200]}"
                )
                return False
                
    except requests.exceptions.Timeout:
        logger.error(f"❌ 서버 요청 타임아웃 (timeout={timeout}초)")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ 서버 연결 실패: {server_url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 요청 중 오류 발생: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """
    메인 실행 함수
    """
    parser = argparse.ArgumentParser(
        description="무신사/싸다구/지마켓 크롤링 결과를 Spring 서버로 전송"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="입력 JSON 파일 경로"
    )
    parser.add_argument(
        "--site-type",
        type=str,
        choices=["auto", "musinsa", "ssadagu", "gmarket"],
        default="auto",
        help="사이트 타입 (auto: 자동 감지, 기본값: auto)"
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:8080/api/v1/crawling/products",
        help="Spring 서버 API 엔드포인트 URL"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="배치 크기 (지정하지 않으면 전체 한 번에 전송)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="요청 타임아웃 (초, 기본값: 30)"
    )
    
    args = parser.parse_args()
    
    # 입력 파일 경로 확인
    if not args.input_file:
        # 기본값: 사이트 타입에 따라 자동 선택
        if args.site_type == "ssadagu":
            default_dir = Path(project_root) / "data" / "ssadagu"
        elif args.site_type == "gmarket":
            default_dir = Path(project_root) / "gmarket_data"
        else:
            default_dir = Path(project_root) / "data" / "musinsa"
        
        if default_dir.exists():
            json_files = list(default_dir.glob("**/*.json"))  # 하위 디렉토리 포함 검색
            if json_files:
                # 최신 파일 찾기
                latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
                input_path = latest_file
                logger.info(f"💡 최신 파일 자동 선택: {input_path.relative_to(project_root)}")
            else:
                logger.error(f"❌ {default_dir} 디렉토리에 JSON 파일이 없습니다")
                return
        else:
            logger.error(f"❌ {default_dir} 디렉토리가 없습니다")
            return
    else:
        input_path = Path(args.input_file)
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        if not input_path.is_absolute():
            input_path = Path(project_root) / input_path
    
    if not input_path.exists():
        logger.error(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        
        # data 디렉토리에서 최신 파일 찾기
        for site in ["musinsa", "ssadagu", "gmarket"]:
            if site == "gmarket":
                data_dir = Path(project_root) / "gmarket_data"
            else:
                data_dir = Path(project_root) / "data" / site
            
            if data_dir.exists():
                json_files = list(data_dir.glob("**/*.json"))  # 하위 디렉토리 포함
                if json_files:
                    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"💡 {data_dir.name}/ 디렉토리에서 최신 파일 발견: {latest_file.name}")
                    logger.info(f"💡 사용 예시: --input-file {latest_file.relative_to(project_root)}")
        return
    
    logger.info(f"📂 입력 파일: {input_path}")
    logger.info(f"🌐 서버 URL: {args.server_url}")
    if args.batch_size:
        logger.info(f"📦 배치 크기: {args.batch_size}")
    
    # JSON 파일 읽기
    try:
        logger.info("JSON 파일 읽는 중...")
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("✅ JSON 파일 읽기 완료")
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 실패: {e}")
        return
    except Exception as e:
        logger.error(f"❌ 파일 읽기 실패: {e}")
        return
    
    # 상품 추출
    try:
        products_list = extract_products(data, site_type=args.site_type, file_path=str(input_path))
        
        if not products_list:
            logger.warning("⚠️  추출된 상품이 없습니다")
            return
        
        logger.info(f"📊 추출된 상품 수: {len(products_list)}개")
        
    except Exception as e:
        logger.error(f"❌ 상품 추출 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    # 서버로 전송
    success = send_to_server(
        products_list,
        server_url=args.server_url,
        batch_size=args.batch_size,
        timeout=args.timeout
    )
    
    if success:
        logger.info("🎉 모든 작업 완료!")
    else:
        logger.error("❌ 서버 전송 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()

