"""
메인 스케줄러 모듈
매일 08:00에 전체 파이프라인 자동 실행 (스텁 포함)
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Optional

import schedule

from storage import DataStorage
from trends.keyword_selector import select_keyword
from utils.logger import logger
from utils.load_env import get_env

# 선택/히스토리 기본값 (keyword_selector 내부 상수와 일치시킴)
DEFAULT_HISTORY_LIMIT = 50


def run_trend_collection(run_id: str, storage: DataStorage) -> Dict[str, str]:
    """
    트렌드 수집 스텁. 추후 네이버 기반 엔진과 연동 예정.
    """
    logger.info("[1/5] 트렌드 수집 스텁 실행 (향후 네이버/엔진 연결 예정)")
    payload = {"run_id": run_id, "status": "skipped", "reason": "trend collection not implemented yet"}
    try:
        storage.save_trends(run_id, payload)
    except Exception as exc:  # pragma: no cover
        logger.warning("트렌드 수집 결과 저장 실패: %s", exc)
    return payload


def run_keyword_selection(run_id: str, storage: DataStorage) -> Optional[str]:
    """
    최신 트렌드/키워드 후보를 읽어 키워드 1개를 선택합니다.
    """
    logger.info("[2/5] 키워드 선택 단계 시작")
    latest_trends = storage.load_latest_trends() or {}
    candidates = latest_trends.get("items") or latest_trends.get("keywords") or []
    # 스텁: 후보가 없으면 샘플 몇 개 사용
    if not candidates:
        candidates = ["샘플키워드1", "샘플키워드2", "샘플키워드3"]
    weighted = get_env("KEYWORD_SELECTION_WEIGHTED", "true").lower() in {"1", "true", "yes"}
    selected = select_keyword(
        candidates,
        history_limit=DEFAULT_HISTORY_LIMIT,
        weighted=weighted,
        storage=storage,
    )
    if selected:
        storage.save_keywords(run_id, {"run_id": run_id, "keywords": [selected], "selected": selected})
        storage.save_run_log(run_id, {"stage": "keyword_selection", "selected_keyword": selected})
    else:
        storage.save_run_log(run_id, {"stage": "keyword_selection", "status": "failed"})
    return selected


def run_product_collection(run_id: str, keyword: Optional[str], storage: DataStorage) -> Dict[str, str]:
    logger.info("[3/5] 상품 수집 스텁 실행 (TODO: ssadagu 연동 예정)")
    if not keyword:
        logger.warning("키워드가 없어 상품 수집을 건너뜁니다.")
        payload = {"status": "skipped", "reason": "no keyword", "run_id": run_id}
    else:
        payload = {"status": "skipped", "keyword": keyword, "reason": "not implemented", "run_id": run_id}
    storage.save_products(run_id, [], meta=payload)
    storage.save_run_log(run_id, {"stage": "product_collection", **payload})
    return payload


def run_content_generation(run_id: str, keyword: Optional[str], storage: DataStorage) -> Dict[str, str]:
    logger.info("[4/5] 콘텐츠 생성 스텁 실행 (TODO: LLM 연동 예정)")
    payload = {"status": "skipped", "run_id": run_id, "keyword": keyword}
    storage.save_post(run_id, payload, meta={"stage": "content_generation"})
    storage.save_run_log(run_id, {"stage": "content_generation", **payload})
    return payload


def run_post_upload(run_id: str, post: Optional[Dict[str, str]], storage: DataStorage) -> Dict[str, str]:
    logger.info("[5/5] 업로드 스텁 실행 (TODO: 블로그 업로드 연동 예정)")
    payload = {"status": "skipped", "run_id": run_id}
    storage.save_run_log(run_id, {"stage": "post_upload", **payload})
    return payload


def run_daily_pipeline(storage: Optional[DataStorage] = None) -> None:
    storage = storage or DataStorage()
    run_id = storage.generate_run_id()
    logger.info("=" * 60)
    logger.info("일일 파이프라인 시작 run_id=%s", run_id)
    logger.info("=" * 60)

    try:
        trend_result = run_trend_collection(run_id, storage)
        keyword = run_keyword_selection(run_id, storage)
        product_result = run_product_collection(run_id, keyword, storage)
        post = run_content_generation(run_id, keyword, storage)
        upload_result = run_post_upload(run_id, post, storage)

        storage.save_run_log(
            run_id,
            {
                "stage": "pipeline_completed",
                "run_id": run_id,
                "trend": trend_result,
                "keyword": keyword,
                "product": product_result,
                "post": post,
                "upload": upload_result,
            },
        )
        logger.info("일일 파이프라인 완료 run_id=%s", run_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("파이프라인 실행 중 예외 발생")
        storage.save_run_log(run_id, {"stage": "pipeline_failed", "run_id": run_id, "error": str(exc)})


def start_scheduler():
    schedule_time = get_env("SCHEDULE_TIME", "08:00")
    logger.info("스케줄러 시작: 매일 %s 실행", schedule_time)
    schedule.every().day.at(schedule_time).do(run_daily_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    # 테스트용: 즉시 한 번 실행
    run_daily_pipeline()
