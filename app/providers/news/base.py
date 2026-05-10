from abc import ABC, abstractmethod

from app.schemas.news import NewsArticleOut


class NewsProvider(ABC):
    provider_name: str

    @abstractmethod
    def get_latest_news(
        self,
        topic: str,
        limit: int = 10,
    ) -> list[NewsArticleOut]:
        pass

    @abstractmethod
    def get_stock_news(
        self,
        symbol: str,
        limit: int = 10,
    ) -> list[NewsArticleOut]:
        pass

    @abstractmethod
    def search_news(
        self,
        query: str,
        limit: int = 10,
        symbols: list[str] | None = None,
    ) -> list[NewsArticleOut]:
        pass