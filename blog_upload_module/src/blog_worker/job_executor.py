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
    payload = _build_payload(request)
    platform = request.blog_type.lower()
    logger.info("워크 %s 업로드 시작 (platform=%s)", request.work_id, platform)

    if platform == "naver":
        result = upload_to_naver_blog(
            payload,
            naver_id=request.blog_id,
            naver_pw=request.blog_password,
            blog_url=request.blog_url,
            headless=False,
        )
    elif platform == "tistory":
        result = upload_to_tistory_blog(
            payload,
            blog_url=request.blog_url,
            kakao_id=request.blog_id,
            kakao_pw=request.blog_password,
            headless=False,
        )
    else:
        message = f"지원하지 않는 blogType: {request.blog_type}"
        logger.error(message)
        result = UploadResult(
            platform=platform or "unknown", success=False, message=message
        )

    if result.posting_url:
        logger.info("업로드 완료 URL: %s", result.posting_url)
    else:
        logger.info("업로드 결과 URL 없음")
    if not result.success:
        logger.error("업로드 실패(work_id=%s): %s", request.work_id, result.message)
    return result
