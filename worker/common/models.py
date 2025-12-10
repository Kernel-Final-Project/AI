from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


def now_iso() -> str:
    """UTC ISO 포맷 타임스탬프 생성."""
    return datetime.utcnow().isoformat()


class TrendCategory(BaseModel):
    category1: str
    category2: Optional[str] = None
    category3: Optional[str] = None


class ProductInfo(BaseModel):
    productId: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    productUrl: Optional[str] = None


class UsedProductInfo(BaseModel):
    productUrl: Optional[str] = None
    name: Optional[str] = None


class WebhookUrls(BaseModel):
    keywordSelect: str
    productSelect: Optional[str] = None
    contentGenerate: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    workId: int
    hasCrawledItems: Optional[bool] = None
    recentTrendKeywords: List[str] = Field(default_factory=list)
    crawledProducts: Optional[List[ProductInfo]] = None
    recentlyUsedProducts: Optional[List[Union[UsedProductInfo, str]]] = None
    trendCategory: TrendCategory
    siteUrl: Optional[str] = None
    webhookSecret: Optional[str] = None
    webhookUrls: WebhookUrls

    @field_validator("recentlyUsedProducts", mode="before")
    @classmethod
    def _normalize_used_products(cls, value: Any) -> Any:
        # 문자열 리스트도 허용하도록 필드 전처리
        if value is None:
            return None
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, (UsedProductInfo, str)):
                    normalized.append(item)
                    continue
                if isinstance(item, dict):
                    normalized.append(UsedProductInfo.model_validate(item))
                    continue
            return normalized
        return value


class KeywordSelectPayload(BaseModel):
    workId: int
    keyword: str
    success: bool = True
    message: str
    startedAt: str = Field(default_factory=now_iso)
    completedAt: str = Field(default_factory=now_iso)
