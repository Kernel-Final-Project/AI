"""
크롤링 관련 Pydantic 모델
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class SiteName(str, Enum):
    """지원하는 사이트 타입"""
    MUSINSA = "musinsa"
    SSADAGU = "ssadagu"
    GMARKET = "gmarket"


class CrawlingRequest(BaseModel):
    """크롤링 요청 DTO
    
    지원 사이트:
    - musinsa: 무신사 크롤링 (실시간)
    - ssadagu: 싸다구 크롤링 (실시간)
    - gmarket: 지마켓 크롤링 (실시간)
    """
    site_name: SiteName = Field(
        ..., 
        description="크롤링할 사이트 이름",
        example="musinsa"
    )
    max_products_per_category: Optional[int] = Field(
        default=10,
        ge=1,
        le=1000,
        description="카테고리당 최대 상품 수"
    )
    categories: Optional[List[str]] = Field(
        default=None,
        description="특정 카테고리만 크롤링 (None이면 전체)"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="크롤링 완료 후 결과를 받을 Spring 서버 URL"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "site_name": "musinsa",
                "max_products_per_category": 10,
                "categories": None,
                "callback_url": "http://localhost:8080/api/v1/crawling/products"
            }
        }


class CrawlingResponse(BaseModel):
    """크롤링 요청 즉시 응답 DTO"""
    task_id: str = Field(..., description="작업 ID (UUID)")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "accepted",
                "message": "크롤링 작업이 시작되었습니다"
            }
        }


class CrawlingStatus(BaseModel):
    """크롤링 작업 상태 조회 DTO"""
    task_id: str = Field(..., description="작업 ID")
    status: str = Field(..., description="작업 상태 (pending, running, completed, failed)")
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="진행률 (0-100)"
    )
    message: Optional[str] = Field(default=None, description="상태 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "progress": 45.5,
                "message": "크롤링 진행 중..."
            }
        }


class Product(BaseModel):
    """상품 데이터 모델 (Spring 서버 DTO와 일치)"""
    site_name: str = Field(..., description="사이트 이름")
    site_url: str = Field(..., description="사이트 URL")
    product_name: str = Field(..., description="상품명")
    product_code: str = Field(..., description="상품 코드")
    product_detail_url: str = Field(..., description="상품 상세 URL")
    product_price: str = Field(default="", description="상품 가격 (String)")
    image_url: str = Field(default="", description="이미지 URL")

    @validator("product_code", "product_name", "product_detail_url")
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError("필수 필드가 비어있습니다")
        return v


class UploadDataResponse(BaseModel):
    """데이터 업로드 응답 DTO"""
    success: bool = Field(..., description="전송 성공 여부")
    message: str = Field(..., description="응답 메시지")
    products_count: int = Field(..., description="전송된 상품 수")
    server_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Spring 서버 응답 (성공 시)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "상품 데이터가 성공적으로 전송되었습니다",
                "products_count": 100,
                "server_response": None
            }
        }


class LoadLatestRequest(BaseModel):
    """최신 JSON 파일 로드 요청 DTO"""
    site_name: SiteName = Field(
        ...,
        description="사이트 이름",
        example="musinsa"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Spring 서버 콜백 URL (None이면 기본 URL 사용)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "site_name": "musinsa",
                "callback_url": "http://localhost:8080/api/v1/crawling/products"
            }
        }

