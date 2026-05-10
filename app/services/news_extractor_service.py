import httpx
import trafilatura


class NewsContentExtractor:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    async def extract_article_text(self, url: str) -> str | None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SparrowBot/1.0; "
                "+https://sparrowlabs.vercel.app)"
            )
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if not extracted:
            return None

        return extracted.strip()