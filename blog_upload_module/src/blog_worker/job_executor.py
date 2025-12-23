"""
Mapping between BlogUploadRequest and blog_upload_module uploaders.
"""

from __future__ import annotations

from typing import Dict

from blog_upload_module import (
    UploadResult,
    upload_to_naver_blog,
    upload_to_tistory_blog,
)

from .logger import logger
from .models import BlogUploadRequest


def _build_payload(request: BlogUploadRequest) -> Dict[str, str]:
    body = request.content or ""
    title = request.title or ""
    return {"title": title, "body_html": body}


def execute_blog_upload(request: BlogUploadRequest) -> UploadResult:
    platform = request.blog_type.lower()
    logger.info(
        "워크 %s 업로드 시작 (platform=%s, isTest=%s)",
        request.work_id,
        platform,
        request.is_test,
    )

    payload = _build_payload(request)
    dry_run = bool(request.is_test)

    if platform == "naver":
        result = upload_to_naver_blog(
            payload,
            naver_id=request.blog_id,
            naver_pw=request.blog_password,
            blog_url=request.blog_url,
            headless=False,
            dry_run=dry_run,
        )
    elif platform == "tistory":
        result = upload_to_tistory_blog(
            payload,
            blog_url=request.blog_url,
            kakao_id=request.blog_id,
            kakao_pw=request.blog_password,
            headless=False,
            dry_run=dry_run,
        )
    else:
        message = f"지원하지 않는 blogType: {request.blog_type}"
        logger.error(message)
        result = UploadResult(
            platform=platform or "unknown", success=False, message=message
        )

    if dry_run:
        result.metadata = dict(result.metadata or {})
        result.metadata.update({"skippedPublish": True, "isTest": True})
        if not result.message:
            result.message = "테스트 요청으로 최종 발행을 생략했습니다."

    if result.posting_url:
        
        logger.info("업로드 완료 URL: %s", result.posting_url)
    else:
        logger.info("업로드 결과 URL 없음")
    if not result.success:
        metadata = result.metadata or {}
        error_code = metadata.get("errorCode")
        if error_code:
            logger.error(
                "업로드 실패(work_id=%s, errorCode=%s): %s",
                request.work_id,
                error_code,
                result.message,
            )
        else:
            logger.error("업로드 실패(work_id=%s): %s", request.work_id, result.message)
    return result
