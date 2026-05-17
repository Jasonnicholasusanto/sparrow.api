from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NewsArticleOut(BaseModel):
    id: str | None = None
    provider: str

    title: str
    summary: str | None = None
    url: str

    source: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None

    symbols: list[str] = Field(default_factory=list)

    sentiment_label: Literal["bullish", "bearish", "neutral"] | None = None
    sentiment_score: float | None = None


class LatestNewsResponse(BaseModel):
    topic: str
    results: list[NewsArticleOut]


class StockNewsResponse(BaseModel):
    symbol: str
    results: list[NewsArticleOut]


class SearchNewsResponse(BaseModel):
    query: str
    results: list[NewsArticleOut]


class StockNewsBatchRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=50)
    limit_per_symbol: int = Field(default=5, ge=1, le=20)


class StockNewsBatchResponse(BaseModel):
    symbols: list[str]
    results: list[NewsArticleOut]


class SummarizeArticleRequest(BaseModel):
    url: str
    title: str | None = None
    source: str | None = None
    summary: str | None = None 


class SummarizeArticleResponse(BaseModel):
    url: str
    summary: str
    sentiment_label: Literal["bullish", "bearish", "neutral"]
    sentiment_score: float = Field(..., ge=-1, le=1)
    key_points: list[str] = Field(default_factory=list)


class ExtractedArticleContent(BaseModel):
    url: str
    final_url: str | None = None
    title: str | None = None
    text: str | None = None
    extraction_status: Literal[
        "full",
        "partial",
        "metadata_only",
        "blocked",
        "failed",
    ]
    source_used: Literal[
        "yahoo",
        "canonical",
        "original_source",
        "metadata",
    ]
    word_count: int = 0