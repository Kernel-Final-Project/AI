"""
blog_upload_module CLI
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .logger import logger, set_log_level
from .naver_uploader import upload_to_naver_blog
from .results import UploadResult
from .tistory_uploader import upload_to_tistory_blog
from .webhook import notify_upload_result


def _read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.exists():
            raise FileNotFoundError(f"본문 파일을 찾을 수 없습니다: {body_path}")
        return body_path.read_text(encoding="utf-8")
    if args.body:
        return args.body
    return """<h2>샘플 포스트</h2>
<p>이 문서는 blog_upload_module 테스트를 위해 자동 업로드되었습니다.</p>
<p>생성 시각: {ts}</p>
""".format(
        ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


def _build_title(args: argparse.Namespace) -> str:
    if args.title:
        return args.title
    return f"[테스트] 자동 업로드 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def _validate_args(args: argparse.Namespace) -> bool:
    if args.platform == "naver":
        missing = []
        if not args.naver_id:
            missing.append("--naver-id")
        if not args.naver_pw:
            missing.append("--naver-pw")
        if not args.naver_blog_url:
            missing.append("--naver-blog-url")
        if missing:
            logger.error("필수 옵션이 누락되었습니다: %s", ", ".join(missing))
            return False

    if args.platform == "tistory":
        missing = []
        if not args.tistory_blog_url:
            missing.append("--tistory-blog-url")
        if missing:
            logger.error("필수 옵션이 누락되었습니다: %s", ", ".join(missing))
            return False
        if not (args.kakao_id and args.kakao_password):
            logger.error(
                "티스토리 업로드에는 카카오 계정(--kakao-id/--kakao-password)이 필요합니다."
            )
            return False

    if args.wait_time <= 0:
        logger.error("--wait-time 값은 1 이상이어야 합니다.")
        return False

    return True


def run_cli():
    parser = argparse.ArgumentParser(description="blog_upload_module standalone uploader")
    parser.add_argument("--platform", choices=["naver", "tistory"], required=True)
    parser.add_argument("--title", help="포스트 제목")
    parser.add_argument("--body", help="본문 문자열 (HTML 가능)")
    parser.add_argument("--body-file", help="본문을 읽어올 파일 경로")
    parser.add_argument("--skip-confirm", action="store_true", help="발행 확인을 생략")
    parser.add_argument("--naver-id", help="네이버 아이디 (플랫폼이 naver인 경우 필수)")
    parser.add_argument(
        "--naver-pw", help="네이버 비밀번호 (플랫폼이 naver인 경우 필수)"
    )
    parser.add_argument(
        "--naver-blog-url",
        help="네이버 블로그 주소 (예: https://blog.naver.com/your_blog)",
    )
    parser.add_argument(
        "--tistory-blog-url",
        help="티스토리 블로그 주소 (예: https://example.tistory.com)",
    )
    parser.add_argument("--kakao-id", help="카카오 로그인 아이디(이메일)")
    parser.add_argument("--kakao-password", help="카카오 로그인 비밀번호")
    parser.add_argument(
        "--headless", action="store_true", help="브라우저 창을 띄우지 않고 실행"
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=10,
        help="기본 WebDriverWait 시간(초). 기본값: 10",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="로그 레벨 (DEBUG/INFO/WARNING/ERROR). 기본값: INFO",
    )
    parser.add_argument("--work-id", help="백엔드 워크 테이블 ID")
    parser.add_argument("--webhook-url", help="업로드 결과를 전송할 웹훅 URL")
    parser.add_argument("--webhook-token", help="웹훅 X-WEBHOOK-SECRET 헤더 값")
    parser.add_argument(
        "--webhook-timeout",
        type=int,
        default=5,
        help="웹훅 HTTP 요청 타임아웃(초). 기본값: 5",
    )
    parser.add_argument(
        "--emit-json",
        action="store_true",
        help="업로드 결과를 JSON 으로 stdout에 출력",
    )
    args = parser.parse_args()

    set_log_level(args.log_level)

    if not _validate_args(args):
        sys.exit(1)

    title = _build_title(args)
    body = _read_body(args)

    logger.info("업로드 플랫폼: %s", args.platform)
    logger.info("제목: %s", title)
    logger.info("본문 길이: %d 자", len(body))

    if not args.skip_confirm:
        confirm = input("실제로 업로드 하시겠습니까? (y/N): ").strip().lower()
        if confirm != "y":
            logger.info("사용자가 업로드를 취소했습니다.")
            sys.exit(0)

    payload = {"title": title, "body_html": body}

    if args.platform == "naver":
        result = upload_to_naver_blog(
            payload,
            naver_id=args.naver_id,
            naver_pw=args.naver_pw,
            blog_url=args.naver_blog_url,
            headless=args.headless,
            wait_time=args.wait_time,
        )
    else:
        result = upload_to_tistory_blog(
            payload,
            blog_url=args.tistory_blog_url,
            kakao_id=args.kakao_id,
            kakao_pw=args.kakao_password,
            headless=args.headless,
            wait_time=args.wait_time,
        )

    completed_at = datetime.now(timezone.utc).isoformat()
    _log_result(result, args.work_id)
    _send_webhook_if_needed(result, args, completed_at)

    if args.emit_json:
        response = result.to_payload(work_id=args.work_id)
        response["completedAt"] = completed_at
        print(json.dumps(response, ensure_ascii=False))

    sys.exit(0 if result.success else 1)


def _log_result(result: UploadResult, work_id: Optional[str]) -> None:
    logger.info("업로드 결과 상태: %s", result.status)
    if work_id:
        logger.info("워크 ID: %s", work_id)
    if result.posting_url:
        logger.info("게시글 URL: %s", result.posting_url)
    if result.message:
        logger.info("결과 메시지: %s", result.message)


def _send_webhook_if_needed(
    result: UploadResult, args: argparse.Namespace, completed_at: str
) -> None:
    notify_upload_result(
        result,
        webhook_url=args.webhook_url,
        token=args.webhook_token,
        timeout=args.webhook_timeout,
        work_id=args.work_id,
        completed_at=completed_at,
        log=logger,
    )


if __name__ == "__main__":
    run_cli()
