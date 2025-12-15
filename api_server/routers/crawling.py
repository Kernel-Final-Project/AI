"""
크롤링 API 라우터
"""
import uuid
import asyncio
import traceback
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from api_server.models.crawling import (
    CrawlingRequest,
    CrawlingResponse,
    CrawlingStatus,
    SiteName,
    UploadDataResponse,
    LoadLatestRequest,
    Product
)
from api_server.services.crawler_service import CrawlerService
from api_server.config import SPRING_SERVER_URL
from utils.logger import logger
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
import json

router = APIRouter(prefix="/api/v1/crawling", tags=["crawling"])

# 작업 상태 저장 (실제 운영에서는 Redis나 DB 사용 권장)
task_status: Dict[str, Dict] = {}

# 크롤링 서비스 인스턴스
crawler_service = CrawlerService()


def send_results_to_spring(
    products_list: list,
    callback_url: str = None,
    task_id: str = None
):
    """
    크롤링 결과를 Spring 서버로 전송
    
    Args:
        products_list: 전송할 상품 리스트
        callback_url: 콜백 URL (None이면 기본 URL 사용)
        task_id: 작업 ID
    """
    try:
        server_url = callback_url or SPRING_SERVER_URL
        
        logger.info(f"[{task_id}] Spring 서버로 결과 전송 시작: {len(products_list)}개 상품")
        
        response = requests.post(
            server_url,
            json=products_list,
            timeout=300  # 5분 타임아웃
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"[{task_id}] ✅ Spring 서버로 결과 전송 성공")
            if task_id:
                task_status[task_id]["status"] = "completed"
                task_status[task_id]["message"] = "크롤링 및 전송 완료"
        else:
            logger.error(
                f"[{task_id}] ❌ Spring 서버 전송 실패: "
                f"상태 코드 {response.status_code}, 응답: {response.text[:200]}"
            )
            if task_id:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["message"] = f"전송 실패: {response.status_code}"
                
    except Exception as e:
        logger.error(f"[{task_id}] Spring 서버 전송 중 오류: {e}")
        if task_id:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["message"] = f"전송 오류: {str(e)}"


def extract_products_from_result(crawl_result: Dict, site_name: str) -> list:
    """
    크롤링 결과에서 상품 리스트 추출
    
    Args:
        crawl_result: 크롤링 결과 딕셔너리
        site_name: 사이트 이름
        
    Returns:
        상품 리스트
    """
    import sys
    from pathlib import Path
    
    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from scripts.send_musinsa_to_server import extract_products
    
    try:
        # extract_products 함수는 Dict를 기대함
        # 모든 사이트 타입이 categories 형태로 변환되어 있음
        products = extract_products(crawl_result, site_type=site_name)
        
        return products
    except Exception as e:
        logger.error(f"상품 추출 중 오류: {e}")
        raise


async def run_crawling_task(
    request: CrawlingRequest,
    task_id: str
):
    """
    백그라운드에서 크롤링 작업 실행
    
    Args:
        request: 크롤링 요청
        task_id: 작업 ID
    """
    try:
        task_status[task_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "크롤링 시작 중..."
        }
        
        logger.info(f"[{task_id}] 크롤링 작업 시작: {request.site_name}")
        
        # 크롤링 실행 (동기 함수를 비동기로 실행)
        loop = asyncio.get_event_loop()
        
        if request.site_name == SiteName.MUSINSA:
            crawl_result = await loop.run_in_executor(
                None,
                crawler_service.crawl_musinsa,
                request.max_products_per_category,
                request.categories
            )
        elif request.site_name == SiteName.SSADAGU:
            crawl_result = await loop.run_in_executor(
                None,
                crawler_service.crawl_ssadagu,
                request.max_products_per_category,
                request.categories
            )
        elif request.site_name == SiteName.GMARKET:
            crawl_result = await loop.run_in_executor(
                None,
                crawler_service.crawl_gmarket,
                request.max_products_per_category,
                request.categories
            )
        else:
            raise ValueError(f"지원하지 않는 사이트: {request.site_name}")
        
        task_status[task_id]["progress"] = 50.0
        task_status[task_id]["message"] = "크롤링 완료, 상품 추출 중..."
        
        logger.info(f"[{task_id}] 크롤링 완료, 상품 추출 시작")
        
        # 상품 추출
        products_list = extract_products_from_result(crawl_result, request.site_name.value)
        
        task_status[task_id]["progress"] = 75.0
        task_status[task_id]["message"] = "Spring 서버로 전송 중..."
        
        logger.info(f"[{task_id}] 추출된 상품 수: {len(products_list)}개")
        
        # Spring 서버로 전송 (동기 함수)
        send_results_to_spring(
            products_list,
            callback_url=request.callback_url,
            task_id=task_id
        )
        
        task_status[task_id]["progress"] = 100.0
        
        logger.info(f"[{task_id}] ✅ 모든 작업 완료")
        
    except Exception as e:
        logger.error(f"[{task_id}] 크롤링 작업 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        task_status[task_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"오류 발생: {str(e)}"
        }


@router.post(
    "/start", 
    response_model=CrawlingResponse,
    responses={
        200: {
            "description": "크롤링 작업이 성공적으로 시작됨",
            "content": {
                "application/json": {
                    "examples": {
                        "musinsa": {
                            "summary": "무신사 크롤링 예시",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "accepted",
                                "message": "크롤링 작업이 시작되었습니다"
                            }
                        },
                        "ssadagu": {
                            "summary": "싸다구 크롤링 예시",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440001",
                                "status": "accepted",
                                "message": "크롤링 작업이 시작되었습니다"
                            }
                        },
                        "gmarket": {
                            "summary": "지마켓 크롤링 예시",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440002",
                                "status": "accepted",
                                "message": "크롤링 작업이 시작되었습니다"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def start_crawling(
    request: CrawlingRequest,
    background_tasks: BackgroundTasks
):
    """
    크롤링 작업 시작
    
    지원 사이트 (site_name 필드에서 선택):
    - **musinsa**: 무신사 크롤링 (실시간)
    - **ssadagu**: 싸다구 크롤링 (실시간)  
    - **gmarket**: 지마켓 크롤링 (실시간)
    
    동작 방식:
    - 즉시 응답 반환 (작업 ID)
    - 백그라운드에서 크롤링 실행
    - 완료 후 Spring 서버로 결과 전송
    """
    # 작업 ID 생성
    task_id = str(uuid.uuid4())
    
    # 작업 상태 초기화
    task_status[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "작업 대기 중..."
    }
    
    # 백그라운드 작업 추가
    background_tasks.add_task(run_crawling_task, request, task_id)
    
    logger.info(f"크롤링 작업 요청 수신: task_id={task_id}, site={request.site_name}")
    
    return CrawlingResponse(
        task_id=task_id,
        status="accepted",
        message="크롤링 작업이 시작되었습니다"
    )


@router.get("/status/{task_id}", response_model=CrawlingStatus)
async def get_crawling_status(task_id: str):
    """
    크롤링 작업 상태 조회
    
    Args:
        task_id: 작업 ID
        
    Returns:
        작업 상태 정보
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    status_info = task_status[task_id]
    
    return CrawlingStatus(
        task_id=task_id,
        status=status_info.get("status", "unknown"),
        progress=status_info.get("progress"),
        message=status_info.get("message")
    )


def validate_product_data(product_dict: Dict) -> Dict:
    """
    상품 데이터 검증 및 정규화
    
    Args:
        product_dict: 상품 데이터 딕셔너리
        
    Returns:
        검증된 상품 데이터 딕셔너리
        
    Raises:
        ValueError: 필수 필드가 누락되었거나 유효하지 않은 경우
    """
    # 필수 필드 확인
    required_fields = ["product_code", "product_name", "product_detail_url"]
    for field in required_fields:
        if field not in product_dict or not product_dict[field] or not str(product_dict[field]).strip():
            raise ValueError(f"필수 필드 '{field}'가 누락되었거나 비어있습니다")
    
    # site_name이 없으면 기본값 설정 (하지만 요청의 site_name과 일치해야 함)
    if "site_name" not in product_dict:
        raise ValueError("'site_name' 필드가 누락되었습니다")
    
    # product_price가 없거나 None이면 빈 문자열로 설정
    product_price = product_dict.get("product_price", "")
    if product_price is None:
        product_price = ""
    else:
        product_price = str(product_price)
    
    # 정규화된 데이터 반환
    return {
        "site_name": str(product_dict["site_name"]).strip(),
        "site_url": str(product_dict.get("site_url", "")).strip(),
        "product_name": str(product_dict["product_name"]).strip(),
        "product_code": str(product_dict["product_code"]).strip(),
        "product_detail_url": str(product_dict["product_detail_url"]).strip(),
        "product_price": product_price,
        "image_url": str(product_dict.get("image_url", "")).strip()
    }


def find_latest_json_file(site_name: str, project_root: Path) -> Optional[Path]:
    """
    사이트별 최신 JSON 파일 찾기
    
    Args:
        site_name: 사이트 이름 (musinsa, ssadagu, gmarket)
        project_root: 프로젝트 루트 경로
        
    Returns:
        최신 JSON 파일 경로 또는 None
    """
    # 사이트별 디렉토리 결정
    if site_name == "gmarket":
        data_dir = project_root / "gmarket_data"
    else:
        data_dir = project_root / "data" / site_name
    
    if not data_dir.exists():
        logger.warning(f"디렉토리가 없습니다: {data_dir}")
        return None
    
    # JSON 파일 찾기 (하위 디렉토리 포함)
    json_files = list(data_dir.glob("**/*.json"))
    
    if not json_files:
        logger.warning(f"JSON 파일을 찾을 수 없습니다: {data_dir}")
        return None
    
    # 최신 파일 찾기 (수정 시간 기준)
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"최신 파일 발견: {latest_file.relative_to(project_root)}")
    
    return latest_file


@router.post("/load-latest", response_model=UploadDataResponse)
async def load_latest_json_file(request: LoadLatestRequest):
    """
    자동으로 최신 JSON 파일을 찾아서 Spring 서버 DB에 저장
    
    사용 시나리오:
    1. Spring 서버가 이 API를 호출 (site_name만 지정)
    2. FastAPI가 자동으로 해당 사이트의 최신 JSON 파일 찾기
       - 무신사: data/musinsa/ 디렉토리에서 최신 파일
       - 싸다구: data/ssadagu/ 디렉토리에서 최신 파일
       - 지마켓: gmarket_data/ 디렉토리에서 최신 파일
    3. 파일 읽어서 상품 추출
    4. 검증 후 Spring 서버 DB로 저장
    
    지원 사이트:
    - **musinsa**: 무신사 크롤링 데이터
    - **ssadagu**: 싸다구 크롤링 데이터
    - **gmarket**: 지마켓 크롤링 데이터
    
    요청 예시:
    ```json
    {
        "site_name": "musinsa",
        "callback_url": "http://localhost:8080/api/v1/crawling/products"
    }
    ```
    
    **callback_url 설명**:
    - Spring 서버의 엔드포인트 URL
    - 기본값: `http://localhost:8080/api/v1/crawling/products`
    - FastAPI가 추출한 상품 데이터를 이 URL로 POST 요청
    - Spring 서버가 이 요청을 받아서 DB에 저장
    """
    try:
        logger.info(f"최신 JSON 파일 로드 요청: site={request.site_name.value}")
        
        # 프로젝트 루트 경로
        project_root = Path(__file__).parent.parent.parent
        
        # 최신 JSON 파일 찾기
        latest_file = find_latest_json_file(request.site_name.value, project_root)
        
        if not latest_file:
            raise HTTPException(
                status_code=404,
                detail=f"{request.site_name.value} 사이트의 JSON 파일을 찾을 수 없습니다"
            )
        
        logger.info(f"파일 읽기 시작: {latest_file}")
        
        # JSON 파일 읽기
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"JSON 파싱 실패: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"파일 읽기 실패: {str(e)}"
            )
        
        # 사이트 타입 자동 감지
        from scripts.send_musinsa_to_server import detect_site_type
        detected_site = detect_site_type(json_data, str(latest_file))
        logger.info(f"자동 감지된 사이트 타입: {detected_site}")
        
        # 요청한 사이트와 일치하는지 확인
        if detected_site != request.site_name.value:
            logger.warning(
                f"사이트 타입 불일치: 요청={request.site_name.value}, 감지={detected_site}"
            )
        
        # 상품 추출
        logger.info(f"상품 추출 시작: site={detected_site}")
        
        from scripts.send_musinsa_to_server import (
            extract_products_musinsa,
            extract_products_ssadagu,
            extract_products_gmarket
        )
        
        if detected_site == "musinsa":
            products = extract_products_musinsa(json_data)
        elif detected_site == "ssadagu":
            products = extract_products_ssadagu(json_data)
        elif detected_site == "gmarket":
            products = extract_products_gmarket(json_data)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 사이트 타입: {detected_site}"
            )
        
        if not products:
            raise HTTPException(
                status_code=400,
                detail="추출된 상품이 없습니다. JSON 파일 형식을 확인해주세요."
            )
        
        logger.info(f"추출된 상품 수: {len(products)}개")
        
        # 상품 데이터 검증 및 정규화
        validated_products = []
        validation_errors = []
        
        for idx, product_dict in enumerate(products):
            try:
                # site_name 일치 확인
                if product_dict.get("site_name") != detected_site:
                    product_dict["site_name"] = detected_site
                
                validated_product = validate_product_data(product_dict)
                validated_products.append(validated_product)
                
            except ValueError as e:
                error_msg = f"상품 {idx+1} 검증 실패: {str(e)}"
                validation_errors.append(error_msg)
                logger.warning(error_msg)
                continue
        
        if not validated_products:
            raise HTTPException(
                status_code=400,
                detail=f"유효한 상품이 없습니다. 검증 오류: {validation_errors[:5]}"
            )
        
        if validation_errors:
            logger.warning(f"일부 상품 검증 실패: {len(validation_errors)}개 (전체: {len(products)}개)")
        
        logger.info(f"검증 완료: {len(validated_products)}개 상품 (실패: {len(validation_errors)}개)")
        
        # Spring 서버로 전송
        server_url = request.callback_url or SPRING_SERVER_URL
        
        logger.info(f"Spring 서버로 전송 시작: {server_url}")
        
        try:
            response = requests.post(
                server_url,
                json=validated_products,
                timeout=10  # 테스트를 위해 타임아웃 단축
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Spring 서버로 데이터 전송 성공: {len(validated_products)}개 상품")
                
                # 응답 파싱 시도
                server_response = None
                try:
                    server_response = response.json()
                except:
                    server_response = {"status_code": response.status_code, "message": response.text[:200]}
                
                return UploadDataResponse(
                    success=True,
                    message=f"{len(validated_products)}개 상품이 성공적으로 전송되었습니다 (파일: {latest_file.name})",
                    products_count=len(validated_products),
                    server_response=server_response
                )
            else:
                error_msg = (
                    f"Spring 서버 전송 실패: "
                    f"상태 코드 {response.status_code}, 응답: {response.text[:200]}"
                )
                logger.error(error_msg)
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_msg
                )
        
        except ConnectionError as e:
            # Spring 서버 연결 실패 (서버가 꺼져있거나 접근 불가)
            error_msg = f"Spring 서버 연결 실패: {server_url} (서버가 실행 중인지 확인하세요)"
            logger.warning(error_msg)
            logger.warning(f"⚠️  파일 읽기 및 상품 추출은 성공했습니다: {len(validated_products)}개 상품")
            
            # 파일 읽기/추출은 성공했으므로 부분 성공으로 반환
            return UploadDataResponse(
                success=False,
                message=f"파일 읽기 및 상품 추출 성공 ({len(validated_products)}개), 하지만 Spring 서버 전송 실패: {str(e)}",
                products_count=len(validated_products),
                server_response={"error": "Connection failed", "url": server_url}
            )
        
        except Timeout as e:
            error_msg = f"Spring 서버 요청 타임아웃: {server_url}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=504,
                detail=error_msg
            )
        
        except RequestException as e:
            error_msg = f"Spring 서버 요청 실패: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=502,
                detail=error_msg
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"최신 파일 로드 중 오류 발생: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

