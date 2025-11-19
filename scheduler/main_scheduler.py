"""
메인 스케줄러 모듈
매일 08:00에 전체 파이프라인 자동 실행
AI1 담당 (파이프라인 통합)
"""
from __future__ import annotations

import schedule
import time
from datetime import datetime
from typing import Dict, List, Optional

from storage import DataStorage
from trends.keyword_selector import select_random_keyword
from trends.trends_collector import collect_and_store_trends
from utils.logger import logger
from utils.load_env import get_env


def _get_trend_target_count() -> int:
    try:
        return max(1, int(get_env("TREND_TARGET_COUNT", "50")))
    except (TypeError, ValueError):
        return 50


def run_full_pipeline(storage: Optional[DataStorage] = None):
    """
    전체 파이프라인을 실행합니다.
    
    1. Google Trends 수집
    2. 키워드 랜덤 선택
    3. ssadagu.kr 상품 수집
    4. AI 콘텐츠 생성
    5. 자체 블로그 업로드
    """
    logger.info("=" * 50)
    logger.info("전체 파이프라인 실행 시작")
    logger.info(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    storage = storage or DataStorage()
    run_id = storage.generate_run_id()
    
    try:
        # 1. 트렌드 수집
        logger.info("[1/5] Google Trends 수집 시작")
        trends = collect_and_store_trends(count=_get_trend_target_count(), storage=storage, metadata={"run_id": run_id})
        if not trends:
            raise RuntimeError("트렌드 데이터를 확보하지 못했습니다.")
        
        # 2. 키워드 선택
        logger.info("[2/5] 키워드 랜덤 선택")
        keyword_history = storage.load_keyword_history()
        weighted = get_env("KEYWORD_SELECTION_WEIGHTED", "false").lower() in {"1", "true", "yes"}
        selected_keyword = select_random_keyword(trends, history=keyword_history, weighted=weighted)
        if not selected_keyword:
            raise RuntimeError("랜덤 키워드 선택에 실패했습니다.")
        storage.save_run_log({"stage": "keyword_selection", "run_id": run_id, "selected_keyword": selected_keyword})
        history_entry = {
            "keyword": selected_keyword.get("keyword"),
            "score": selected_keyword.get("score"),
            "run_id": run_id,
            "selected_at": datetime.now().isoformat(),
        }
        storage.save_keyword_history(keyword_history + [history_entry])
        
        # 3. 상품 수집 (스텁)
        logger.info("[3/5] ssadagu.kr 상품 수집 (준비 중)")
        products = _placeholder_collect_products(selected_keyword)
        if products:
            storage.save_products(products, metadata={"keyword": selected_keyword.get("keyword"), "run_id": run_id})
        
        # 4. 콘텐츠 생성 (스텁)
        logger.info("[4/5] AI 콘텐츠 생성 (준비 중)")
        post_payload = _placeholder_generate_content(selected_keyword, products)
        if post_payload:
            storage.save_post(post_payload, metadata={"keyword": selected_keyword.get("keyword"), "run_id": run_id})
        
        # 5. 블로그 업로드 (스텁)
        logger.info("[5/5] 자체 블로그 업로드 (준비 중)")
        _placeholder_upload_post(post_payload)
        
        logger.info("=" * 50)
        logger.info("전체 파이프라인 실행 완료")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}")
        storage.save_run_log({"stage": "pipeline_error", "run_id": run_id, "error": str(e)})
        raise


def _placeholder_collect_products(selected_keyword: Dict) -> List[Dict]:
    """
    ssadagu.kr 상품 수집 스텁 (추후 실제 크롤러로 교체 예정)
    """
    logger.debug("상품 수집 스텁 실행: 실제 구현 시 ssadagu 모듈 호출 예정")
    return []


def _placeholder_generate_content(selected_keyword: Dict, products: List[Dict]) -> Optional[Dict]:
    """
    콘텐츠 생성 스텁
    """
    logger.debug("콘텐츠 생성 스텁 실행: 실제 구현 시 LLM 모듈 호출 예정")
    return None


def _placeholder_upload_post(post_payload: Optional[Dict]) -> None:
    """
    블로그 업로드 스텁
    """
    logger.debug("블로그 업로드 스텁 실행: 실제 구현 시 자체 블로그 API 호출 예정")


def start_scheduler():
    """
    스케줄러를 시작합니다.
    매일 08:00에 자동 실행
    """
    schedule_time = get_env('SCHEDULE_TIME', '08:00')
    
    logger.info(f"스케줄러 시작: 매일 {schedule_time}에 실행")
    schedule.every().day.at(schedule_time).do(run_full_pipeline)
    
    # 즉시 한 번 실행 (테스트용)
    # run_full_pipeline()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크


if __name__ == "__main__":
    logger.info("스케줄러 시작")
    start_scheduler()
