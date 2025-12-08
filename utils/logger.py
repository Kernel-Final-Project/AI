"""
로깅 유틸리티
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "ai_blog_project", log_level: str = None) -> logging.Logger:
    """
    로거를 설정합니다.
    
    Args:
        name: 로거 이름
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 중복 생성 방지
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# 기본 로거 인스턴스 생성
import os
logger = setup_logger()

