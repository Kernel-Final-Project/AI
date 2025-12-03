"""
블로그 업로더 테스트 스크립트
네이버/티스토리 봇이 정상 작동하는지 확인합니다.

사용법:
    python test_blog_uploaders.py              # 둘 다 테스트
    python test_blog_uploaders.py --naver      # 네이버만
    python test_blog_uploaders.py --tistory    # 티스토리만
"""

import sys
import argparse
from datetime import datetime
from utils.logger import logger
from utils.load_env import get_env


def check_naver_env():
    """네이버 블로그 환경변수 확인"""
    logger.info("=" * 60)
    logger.info("네이버 블로그 환경변수 확인")
    logger.info("=" * 60)

    naver_id = get_env('NAVER_ID')
    naver_pw = get_env('NAVER_PW')
    blog_url = get_env('NAVER_BLOG_URL')

    checks = {
        'NAVER_ID': naver_id,
        'NAVER_PW': '***' if naver_pw else None,
        'BLOG_URL': blog_url,
    }

    all_ok = True
    for key, value in checks.items():
        status = "설정됨" if value else "미설정"
        logger.info(f"  {key}: {status}")
        if not value:
            all_ok = False

    logger.info("")
    return all_ok


def check_tistory_env():
    """티스토리 블로그 환경변수 확인"""
    logger.info("=" * 60)
    logger.info("티스토리 블로그 환경변수 확인")
    logger.info("=" * 60)

    kakao_id = get_env('KAKAO_ID') or get_env('TISTORY_ID')
    kakao_pw = get_env('KAKAO_PASSWORD') or get_env('TISTORY_PW')
    blog_url = get_env('TISTORY_BLOG_URL')

    checks = {
        'KAKAO_ID (또는 TISTORY_ID)': kakao_id,
        'KAKAO_PASSWORD (또는 TISTORY_PW)': '***' if kakao_pw else None,
        'TISTORY_BLOG_URL': blog_url,
    }

    all_ok = True
    for key, value in checks.items():
        status = "설정됨" if value else "미설정"
        logger.info(f"  {key}: {status}")
        if not value:
            all_ok = False

    logger.info("")
    return all_ok


def test_naver_upload():
    """네이버 블로그 업로드 테스트"""
    logger.info("=" * 60)
    logger.info("네이버 블로그 업로드 테스트 시작")
    logger.info("=" * 60)

    # 환경변수 확인
    if not check_naver_env():
        logger.error("네이버 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return False

    try:
        from auto_posting.naver_uploader import upload_to_naver_blog

        # 테스트 콘텐츠
        test_content = {
            'title': f'[테스트] 네이버 블로그 봇 테스트 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'body_html': '''
<h2>테스트 포스트입니다</h2>
<p>이 글은 자동 업로드 봇 테스트를 위해 작성되었습니다.</p>

<h3>테스트 내용</h3>
<ul>
    <li>자동 로그인 테스트</li>
    <li>제목 입력 테스트</li>
    <li>본문 입력 테스트</li>
    <li>발행 버튼 클릭 테스트</li>
</ul>

<p><strong>테스트 시간:</strong> ''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''</p>
<p><em>이 글은 테스트 후 삭제하셔도 됩니다.</em></p>
            ''',
        }

        logger.info("테스트 콘텐츠:")
        logger.info(f"  제목: {test_content['title']}")
        logger.info(f"  본문 길이: {len(test_content['body_html'])} 자")
        logger.info("")

        # 실제 업로드 (사용자 확인)
        user_input = input("실제로 블로그에 테스트 글을 올리시겠습니까? (y/n): ").strip().lower()
        if user_input != 'y':
            logger.info("테스트를 건너뜁니다.")
            return False

        logger.info("업로드 시작...")
        success = upload_to_naver_blog(test_content)

        if success:
            logger.info(" 네이버 블로그 업로드 테스트 성공!")
            return True
        else:
            logger.error("네이버 블로그 업로드 테스트 실패")
            return False

    except Exception as e:
        logger.error(f"네이버 블로그 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tistory_upload():
    """티스토리 블로그 업로드 테스트"""
    logger.info("=" * 60)
    logger.info("티스토리 블로그 업로드 테스트 시작")
    logger.info("=" * 60)

    # 환경변수 확인
    if not check_tistory_env():
        logger.error("티스토리 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return False

    try:
        from auto_posting.tistory_uploader import upload_to_tistory_blog

        # 테스트 콘텐츠
        test_content = {
            'title': f'[테스트] 티스토리 블로그 봇 테스트 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'content': f'''테스트 포스트입니다

이 글은 자동 업로드 봇 테스트를 위해 작성되었습니다.

테스트 내용:
- 자동 로그인 테스트 (카카오 계정)
- 제목 입력 테스트
- 본문 입력 테스트
- 발행 버튼 클릭 테스트

테스트 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

이 글은 테스트 후 삭제하셔도 됩니다.
            ''',
        }

        logger.info("테스트 콘텐츠:")
        logger.info(f"  제목: {test_content['title']}")
        logger.info(f"  본문 길이: {len(test_content['content'])} 자")
        logger.info("")

        # 실제 업로드 (사용자 확인)
        user_input = input("⚠️  실제로 블로그에 테스트 글을 올리시겠습니까? (y/n): ").strip().lower()
        if user_input != 'y':
            logger.info("테스트를 건너뜁니다.")
            return False

        logger.info("업로드 시작...")
        success = upload_to_tistory_blog(test_content)

        if success:
            logger.info("티스토리 블로그 업로드 테스트 성공!")
            return True
        else:
            logger.error("티스토리 블로그 업로드 테스트 실패")
            return False

    except Exception as e:
        logger.error(f" 티스토리 블로그 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='블로그 업로더 테스트')
    parser.add_argument('--naver', action='store_true', help='네이버 블로그만 테스트')
    parser.add_argument('--tistory', action='store_true', help='티스토리 블로그만 테스트')
    parser.add_argument('--env-only', action='store_true', help='환경변수 확인만 (업로드 X)')
    args = parser.parse_args()

    logger.info("")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 15 + "블로그 업로더 테스트" + " " * 22 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("")

    results = {}

    # 테스트 대상 결정
    test_naver = args.naver or (not args.tistory)
    test_tistory = args.tistory or (not args.naver)

    # 환경변수 확인만
    if args.env_only:
        if test_naver:
            check_naver_env()
        if test_tistory:
            check_tistory_env()
        return

    # 네이버 테스트
    if test_naver:
        results['naver'] = test_naver_upload()
        logger.info("")

    # 티스토리 테스트
    if test_tistory:
        results['tistory'] = test_tistory_upload()
        logger.info("")

    # 결과 요약
    logger.info("=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)

    for platform, success in results.items():
        status = "성공" if success else " 실패"
        logger.info(f"  {platform.upper()}: {status}")

    logger.info("")

    # 종료 코드
    all_success = all(results.values()) if results else False
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
