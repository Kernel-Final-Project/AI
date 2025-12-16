"""
FastAPI 메인 애플리케이션
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from api_server.config import API_HOST, API_PORT, ROOT_PATH
from api_server.routers import crawling

# FastAPI 앱 생성
app = FastAPI(
    title="Crawling API Server",
    description="크롤링 작업을 처리하는 FastAPI 서버",
    version="1.0.0",
    root_path=ROOT_PATH if ROOT_PATH else None
)

# 라우터 등록
app.include_router(crawling.router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Crawling API Server",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True  # 개발 모드
    )
