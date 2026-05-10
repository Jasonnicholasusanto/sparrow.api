from datetime import datetime, timezone

from app.providers.news.base import NewsProvider
from app.providers.news.yfinance_news_provider import YFinanceNewsProvider
from app.schemas.news import (
    LatestNewsResponse,
    NewsArticleOut,
    SearchNewsResponse,
    StockNewsBatchResponse,
    StockNewsResponse,
)


class NewsService:
    def __init__(
        self,
        providers: list[NewsProvider] | None = None,
    ) -> None:
        self.providers = providers or [YFinanceNewsProvider()]

    def get_latest_news(
        self,
        topic: str = "financial markets",
        limit: int = 10,
    ) -> LatestNewsResponse:
        articles: list[NewsArticleOut] = []

        for provider in self.providers:
            provider_articles = provider.get_latest_news(
                topic=topic,
                limit=limit,
            )
            articles.extend(provider_articles)

        return LatestNewsResponse(
            topic=topic,
            results=self._dedupe_and_sort_articles(articles)[:limit],
        )

    def get_stock_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> StockNewsResponse:
        clean_symbol = symbol.upper().strip()
        articles: list[NewsArticleOut] = []

        for provider in self.providers:
            provider_articles = provider.get_stock_news(
                symbol=clean_symbol,
                limit=limit,
            )
            articles.extend(provider_articles)

        return StockNewsResponse(
            symbol=clean_symbol,
            results=self._dedupe_and_sort_articles(articles)[:limit],
        )

    def search_news(
        self,
        query: str,
        limit: int = 10,
    ) -> SearchNewsResponse:
        articles: list[NewsArticleOut] = []

        for provider in self.providers:
            provider_articles = provider.search_news(
                query=query,
                limit=limit,
            )
            articles.extend(provider_articles)

        return SearchNewsResponse(
            query=query,
            results=self._dedupe_and_sort_articles(articles)[:limit],
        )

    def search_stock_news(
        self,
        symbol: str,
        query: str,
        limit: int = 10,
    ) -> SearchNewsResponse:
        clean_symbol = symbol.upper().strip()
        search_query = f"{clean_symbol} {query}".strip()

        articles: list[NewsArticleOut] = []

        for provider in self.providers:
            provider_articles = provider.search_news(
                query=search_query,
                limit=limit,
                symbols=[clean_symbol],
            )
            articles.extend(provider_articles)

        return SearchNewsResponse(
            query=search_query,
            results=self._dedupe_and_sort_articles(articles)[:limit],
        )

    def get_batch_stock_news(
        self,
        symbols: list[str],
        limit_per_symbol: int = 5,
    ) -> StockNewsBatchResponse:
        clean_symbols = sorted(
            {
                symbol.upper().strip()
                for symbol in symbols
                if symbol and symbol.strip()
            }
        )

        articles: list[NewsArticleOut] = []

        for symbol in clean_symbols:
            for provider in self.providers:
                provider_articles = provider.get_stock_news(
                    symbol=symbol,
                    limit=limit_per_symbol,
                )
                articles.extend(provider_articles)

        return StockNewsBatchResponse(
            symbols=clean_symbols,
            results=self._dedupe_and_sort_articles(articles),
        )

    def _dedupe_and_sort_articles(
        self,
        articles: list[NewsArticleOut],
    ) -> list[NewsArticleOut]:
        seen: set[str] = set()
        deduped: list[NewsArticleOut] = []

        for article in articles:
            key = article.url.lower().strip()

            if key in seen:
                continue

            seen.add(key)
            deduped.append(article)

        return sorted(
            deduped,
            key=lambda article: article.published_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )