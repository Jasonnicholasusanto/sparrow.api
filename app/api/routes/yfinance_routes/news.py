from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.profile import get_current_profile
from app.schemas.news import (
    ExtractedArticleContent,
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
    

@router.post("/articles/retrieve", response_model=ExtractedArticleContent)
async def retrieve_article_content(
    url: str = Query(..., description="URL of the news article to retrieve"),
    title: str | None = Query(None, description="Fallback article title"),
    summary: str | None = Query(None, description="Fallback article summary"),
    user=Depends(get_current_profile),
):
    try:
        extractor = NewsContentExtractor()

        extracted = await extractor.extract_article_content(
            url=url,
            fallback_title=title,
            fallback_summary=summary,
        )

        if not extracted.text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract readable article text from URL.",
            )

        return extracted

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve article content: {str(e)}",
        )
    

# @router.post("/articles/summarize", response_model=SummarizeArticleResponse)
# async def summarize_news_article(
#     request: SummarizeArticleRequest, 
#     user=Depends(get_current_profile)
# ):
#     try:
#         extractor = NewsContentExtractor()
#         extracted = await extractor.extract_article_content(
#             url=request.url,
#             fallback_title=request.title,
#             fallback_summary=request.summary,
#         )

#         if not extracted:
#             raise HTTPException(
#                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#                 detail="Could not extract readable article text from URL.",
#             )

#         ai_service = NewsAIService()

#         return await ai_service.summarize_article(
#             url=request.url,
#             extracted=extracted,
#             title=request.title,
#             source=request.source,
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to summarize article: {str(e)}",
#         )