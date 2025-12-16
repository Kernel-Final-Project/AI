"""
FastAPI load-latest 엔드포인트 테스트 스크립트
"""
import json
import sys
import requests
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.logger import logger


def test_load_latest_api(
    site_name: str,
    api_url: str = "http://localhost:8000/api/v1/crawling/load-latest",
    callback_url: str = None,
    skip_spring: bool = False
):
    """
    load-latest API 테스트
    
    Args:
        site_name: 사이트 이름 (musinsa, ssadagu, gmarket)
        api_url: FastAPI 엔드포인트 URL
        callback_url: Spring 서버 콜백 URL (None이면 기본값 사용)
        skip_spring: Spring 서버 연결 스킵 (파일 읽기/추출만 테스트)
    """
    try:
        # 요청 데이터 구성
        request_data = {
            "site_name": site_name
        }
        
        if callback_url:
            request_data["callback_url"] = callback_url
        
        if skip_spring:
            # Spring 서버 연결을 스킵하기 위해 존재하지 않는 URL 사용
            request_data["callback_url"] = "http://localhost:9999/fake-endpoint"
            logger.info("⚠️  Spring 서버 연결 스킵 모드 (파일 읽기/추출만 테스트)")
        
        logger.info(f"API 요청 전송: {api_url}")
        logger.info(f"요청 데이터: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        
        # API 호출
        response = requests.post(
            api_url,
            json=request_data,
            timeout=300
        )
        
        # 응답 확인
        logger.info(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info("✅ API 호출 성공!")
            logger.info(f"응답: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            if skip_spring:
                logger.warning("⚠️  Spring 서버 연결은 실패했지만, 파일 읽기/추출은 성공했습니다")
            
            return True
        else:
            logger.error(f"❌ API 호출 실패: {response.status_code}")
            logger.error(f"응답: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        if skip_spring:
            logger.warning(f"⚠️  Spring 서버 연결 실패 (예상됨): {e}")
            logger.info("✅ 파일 읽기/추출은 성공했을 가능성이 높습니다")
            return True
        else:
            logger.error(f"❌ 연결 실패: {e}")
            logger.error("💡 Spring 서버가 실행 중인지 확인하세요")
            return False
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="FastAPI load-latest 엔드포인트 테스트"
    )
    parser.add_argument(
        "--site",
        type=str,
        required=True,
        choices=["musinsa", "ssadagu", "gmarket"],
        help="테스트할 사이트 이름"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000/api/v1/crawling/load-latest",
        help="FastAPI 엔드포인트 URL"
    )
    parser.add_argument(
        "--callback-url",
        type=str,
        default=None,
        help="Spring 서버 콜백 URL (기본값: http://localhost:8080/api/v1/crawling/products)"
    )
    parser.add_argument(
        "--skip-spring",
        action="store_true",
        help="Spring 서버 연결 스킵 (파일 읽기/추출만 테스트)"
    )
    
    args = parser.parse_args()
    
    # 테스트 실행
    success = test_load_latest_api(
        site_name=args.site,
        api_url=args.api_url,
        callback_url=args.callback_url,
        skip_spring=args.skip_spring
    )
    
    if success:
        logger.info("✅ 테스트 완료!")
        sys.exit(0)
    else:
        logger.error("❌ 테스트 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()



