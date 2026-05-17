from datetime import datetime, timezone
import hashlib
from typing import Any

import yfinance as yf

from app.providers.news.base import NewsProvider
from app.schemas.news import NewsArticleOut


class YFinanceNewsProvider(NewsProvider):
    provider_name = "yfinance"

    def get_latest_news(
        self,
        topic: str = "financial markets",
        limit: int = 10,
    ) -> list[NewsArticleOut]:
        """
        yfinance does not have a true generic latest-news endpoint.
        This uses Yahoo Finance search news as an MVP approximation.
        """
        return self.search_news(
            query=topic,
            limit=limit,
        )

    def get_stock_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> list[NewsArticleOut]:
        symbol = symbol.upper().strip()

        try:
            ticker = yf.Ticker(symbol)
            raw_news = ticker.news or []
        except Exception:
            return []

        articles: list[NewsArticleOut] = []

        for item in raw_news[:limit]:
            article = self._normalise_article(
                item=item,
                fallback_symbols=[symbol],
            )

            if article:
                articles.append(article)

        return articles

    def search_news(
        self,
        query: str,
        limit: int = 10,
        symbols: list[str] | None = None,
    ) -> list[NewsArticleOut]:
        query = query.strip()

        if not query:
            return []

        try:
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
            raw_news = search.news or []
        except Exception:
            return []

        articles: list[NewsArticleOut] = []

        for item in raw_news[:limit]:
            article = self._normalise_article(
                item=item,
                fallback_symbols=symbols or [],
            )

            if article:
                articles.append(article)

        return articles

    def _normalise_article(
        self,
        item: dict[str, Any],
        fallback_symbols: list[str],
    ) -> NewsArticleOut | None:
        """
        yfinance news payloads can be inconsistent:
        sometimes fields are directly on item,
        sometimes under item["content"].
        """

        content = item.get("content") if isinstance(item.get("content"), dict) else item

        title = content.get("title")
        if not title:
            return None

        url = self._extract_url(content)
        if not url:
            return None

        summary = (
            content.get("summary")
            or content.get("description")
            or content.get("shortDescription")
        )

        source = self._extract_source(content)
        image_url = self._extract_image_url(content)
        published_at = self._extract_published_at(content)

        related_tickers = (
            content.get("relatedTickers")
            or content.get("related_tickers")
            or []
        )

        symbols = sorted(
            {
                *[symbol.upper().strip() for symbol in fallback_symbols if symbol],
                *[str(symbol).upper().strip() for symbol in related_tickers if symbol],
            }
        )

        external_id = content.get("id") or content.get("uuid")

        if not external_id:
            external_id = hashlib.sha256(
                f"{title}:{url}".encode("utf-8")
            ).hexdigest()

        return NewsArticleOut(
            id=external_id,
            provider=self.provider_name,
            title=title,
            summary=summary,
            url=url,
            source=source,
            image_url=image_url,
            published_at=published_at,
            symbols=symbols,
        )

    def _extract_url(self, content: dict[str, Any]) -> str | None:
        canonical_url = content.get("canonicalUrl")
        clickthrough_url = content.get("clickThroughUrl")

        if isinstance(canonical_url, dict) and canonical_url.get("url"):
            return canonical_url["url"]

        if isinstance(clickthrough_url, dict) and clickthrough_url.get("url"):
            return clickthrough_url["url"]

        return content.get("link") or content.get("url")

    def _extract_source(self, content: dict[str, Any]) -> str | None:
        provider = content.get("provider")

        if isinstance(provider, dict):
            return provider.get("displayName") or provider.get("name")

        return content.get("publisher") or content.get("source")

    def _extract_image_url(self, content: dict[str, Any]) -> str | None:
        thumbnail = content.get("thumbnail")

        if not isinstance(thumbnail, dict):
            return None

        resolutions = thumbnail.get("resolutions") or []

        if not resolutions:
            return None

        return resolutions[-1].get("url")

    def _extract_published_at(self, content: dict[str, Any]) -> datetime | None:
        published = (
            content.get("pubDate")
            or content.get("displayTime")
            or content.get("providerPublishTime")
        )

        if isinstance(published, int):
            return datetime.fromtimestamp(published, tz=timezone.utc)

        if isinstance(published, str):
            try:
                return datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                return None

        return None