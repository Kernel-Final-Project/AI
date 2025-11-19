"""
환경변수 로드 유틸리티
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# 환경변수 자동 로드
load_dotenv()

# 주요 환경변수 변수로 직접 할당
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def load_environment():
    """
    .env 파일에서 환경변수를 로드합니다.
    """
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    return True


def get_env(key: str, default: str = None) -> str:
    """
    환경변수를 가져옵니다.
    
    Args:
        key: 환경변수 키
        default: 기본값
        
    Returns:
        환경변수 값
    """
    return os.getenv(key, default)

