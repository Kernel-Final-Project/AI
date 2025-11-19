"""
AI 콘텐츠 생성 엔진
AI2 담당
"""
from content_ai.gpt_utils import get_client
from utils.logger import logger


def test_openai_connection():
    """OpenAI 연결 테스트"""
    try:
        client = get_client()
        response = client.generate_text(
            system_prompt="당신은 도움이 되는 AI 어시스턴트입니다.",
            user_prompt="'테스트 성공'이라고만 답해주세요."
        )
        logger.info(f"연결 테스트 성공: {response}")
        print(f"✅ 연결 테스트 성공: {response}")
        return True
    except Exception as e:
        logger.error(f"연결 테스트 실패: {e}")
        print(f"❌ 연결 테스트 실패: {e}")
        return False
