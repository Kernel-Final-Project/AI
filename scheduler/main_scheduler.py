"""
메인 스케줄러 모듈
매일 08:00에 전체 파이프라인 자동 실행
AI1 담당 (파이프라인 통합)
"""
import schedule
import time
from datetime import datetime
from utils.logger import logger
from utils.load_env import get_env


def run_full_pipeline():
    """
    전체 파이프라인을 실행합니다.
    
    1. Google Trends 수집
    2. 키워드 랜덤 선택
    3. ssadagu.kr 상품 수집
    4. AI 콘텐츠 생성
    5. 네이버 블로그 업로드
    """
    logger.info("=" * 50)
    logger.info("전체 파이프라인 실행 시작")
    logger.info(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 1. 트렌드 수집
        logger.info("[1/5] Google Trends 수집 시작")
        # TODO: trends.trends_collector.collect_trends() 호출
        
        # 2. 키워드 선택
        logger.info("[2/5] 키워드 랜덤 선택")
        # TODO: trends.keyword_selector.select_random_keyword() 호출
        
        # 3. 상품 수집
        logger.info("[3/5] ssadagu.kr 상품 수집")
        # TODO: ssadagu.ssadagu_scraper.search_products() 호출
        
        # 4. 콘텐츠 생성
        logger.info("[4/5] AI 콘텐츠 생성")
        # TODO: content_ai.content_generator.generate_full_content() 호출
        
        # 5. 블로그 업로드
        logger.info("[5/5] 네이버 블로그 업로드")
        # TODO: auto_posting.naver_uploader.upload_to_naver_blog() 호출
        
        logger.info("=" * 50)
        logger.info("전체 파이프라인 실행 완료")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류 발생: {e}")
        raise


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

