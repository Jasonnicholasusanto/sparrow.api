from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.profile import get_current_profile
from app.schemas.news import (
    LatestNewsResponse,
    SearchNewsResponse,
    StockNewsBatchRequest,
    StockNewsBatchResponse,
    StockNewsResponse,
    SummarizeArticleRequest,
    SummarizeArticleResponse,
)
from app.services.ai.news_service import NewsAIService
from app.services.news_extractor_service import NewsContentExtractor
from app.services.news_service import NewsService
import yfinance as yf


router = APIRouter(prefix="/news", tags=["News"])


def get_news_service() -> NewsService:
    return NewsService()


@router.get("/test")
async def test_news_provider(query: str = Query(default="test"), limit: int = Query(default=10)):
    search = yf.Search(
                query=query,
                max_results=0,
                news_count=limit,
                lists_count=0,
                include_research=False,
                include_cultural_assets=False,
                enable_fuzzy_query=True,
                raise_errors=False,
            )
    search.search()
    return search.news


@router.get("/latest", response_model=LatestNewsResponse)
async def get_latest_news(
    topic: str = Query(
        default="financial markets",
        description="Topic to search Yahoo Finance news for.",
    ),
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_profile),
    news_service: NewsService = Depends(get_news_service),
):
    try:
        return news_service.get_latest_news(
            topic=topic,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch latest news: {str(e)}",
        )


@router.get("/stocks/{symbol}", response_model=StockNewsResponse)
async def get_stock_news(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_profile),
    news_service: NewsService = Depends(get_news_service),
):
    try:
        return news_service.get_stock_news(
            symbol=symbol,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch news for '{symbol}': {str(e)}",
        )


@router.get("/stocks/{symbol}/search", response_model=SearchNewsResponse)
async def search_stock_news(
    symbol: str,
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_profile),
    news_service: NewsService = Depends(get_news_service),
):
    try:
        return news_service.search_stock_news(
            symbol=symbol,
            query=query,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search news for '{symbol}': {str(e)}",
        )


@router.post("/stocks/batch", response_model=StockNewsBatchResponse)
async def get_batch_stock_news(
    request: StockNewsBatchRequest,
    user=Depends(get_current_profile),
    news_service: NewsService = Depends(get_news_service),
):
    try:
        return news_service.get_batch_stock_news(
            symbols=request.symbols,
            limit_per_symbol=request.limit_per_symbol,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch stock news: {str(e)}",
        )


@router.get("/search", response_model=SearchNewsResponse)
async def search_news(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    user=Depends(get_current_profile),
    news_service: NewsService = Depends(get_news_service),
):
    try:
        return news_service.search_news(
            query=query,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search news: {str(e)}",
        )
    

@router.post("/articles/summarize", response_model=SummarizeArticleResponse)
async def summarize_news_article(request: SummarizeArticleRequest):
    try:
        extractor = NewsContentExtractor()
        article_text = await extractor.extract_article_text(request.url)

        if not article_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable article text from URL.",
            )

        ai_service = NewsAIService()

        return await ai_service.summarize_article(
            url=request.url,
            article_text=article_text,
            title=request.title,
            source=request.source,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize article: {str(e)}",
        )