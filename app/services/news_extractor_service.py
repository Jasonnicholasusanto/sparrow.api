import re
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.schemas.news import ExtractedArticleContent


ExtractionStatus = Literal[
    "full",
    "partial",
    "metadata_only",
    "blocked",
    "failed",
]

SourceUsed = Literal[
    "yahoo",
    "continue_reading",
    "canonical",
    "original_source",
    "metadata",
]


class NewsContentExtractor:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    async def extract_article_content(
        self,
        url: str,
        fallback_title: str | None = None,
        fallback_summary: str | None = None,
    ) -> ExtractedArticleContent:
        """
        Main extraction flow:

        1. Try extracting from the provided URL.
        2. If content is full, return it.
        3. If content is partial/metadata-only, try Yahoo's "Continue reading" URL.
        4. If that fails, try canonical/og URL.
        5. If all fails, return partial text or metadata-only fallback.
        """

        html, final_url, status_code = await self._fetch_html(url)

        if status_code in {401, 403, 429}:
            return self._metadata_only(
                url=url,
                final_url=final_url or url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                status="blocked",
            )

        if not html:
            return self._metadata_only(
                url=url,
                final_url=final_url or url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                status="failed",
            )

        base_url = final_url or url

        text = self._extract_text(html)
        quality = self._classify_quality(text)

        if quality == "full":
            return ExtractedArticleContent(
                url=url,
                final_url=final_url,
                title=fallback_title,
                text=text,
                extraction_status="full",
                source_used=self._source_type(base_url),
                word_count=self._word_count(text),
            )

        # Yahoo often has partial text and a "Continue reading" link
        # to the original publisher.
        continue_reading_url = self._extract_continue_reading_url(
            html=html,
            base_url=base_url,
        )

        if continue_reading_url and not self._same_url(continue_reading_url, url):
            continue_result = await self._try_extract_from_url(
                target_url=continue_reading_url,
                original_url=url,
                fallback_title=fallback_title,
                source_used="continue_reading",
            )

            if continue_result and continue_result.extraction_status in {
                "full",
                "partial",
            }:
                return continue_result

        # If no continue-reading URL works, try canonical / og:url / parsely-link.
        canonical_url = self._extract_canonical_url(html)

        if (
            canonical_url
            and not self._same_url(canonical_url, url)
            and not self._same_url(canonical_url, continue_reading_url)
        ):
            canonical_result = await self._try_extract_from_url(
                target_url=canonical_url,
                original_url=url,
                fallback_title=fallback_title,
                source_used="canonical",
            )

            if canonical_result and canonical_result.extraction_status in {
                "full",
                "partial",
            }:
                return canonical_result

        # If the original URL produced some usable text, return it as partial.
        if text:
            return ExtractedArticleContent(
                url=url,
                final_url=final_url,
                title=fallback_title,
                text=text,
                extraction_status="partial",
                source_used=self._source_type(base_url),
                word_count=self._word_count(text),
            )

        # Last fallback: title/summary metadata only.
        return self._metadata_only(
            url=url,
            final_url=final_url or url,
            fallback_title=fallback_title,
            fallback_summary=fallback_summary,
            status="metadata_only",
        )

    async def _try_extract_from_url(
        self,
        target_url: str,
        original_url: str,
        fallback_title: str | None,
        source_used: Literal["continue_reading", "canonical"],
    ) -> ExtractedArticleContent | None:
        html, final_url, status_code = await self._fetch_html(target_url)

        if status_code in {401, 403, 429} or not html:
            return None

        text = self._extract_text(html)
        quality = self._classify_quality(text)

        if quality == "metadata_only":
            return None

        return ExtractedArticleContent(
            url=original_url,
            final_url=final_url or target_url,
            title=fallback_title,
            text=text,
            extraction_status=quality,
            source_used=source_used,
            word_count=self._word_count(text),
        )

    async def _fetch_html(
        self,
        url: str,
    ) -> tuple[str | None, str | None, int | None]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; SparrowBot/1.0; "
                "+https://sparrowlabs.vercel.app)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)

            if response.status_code >= 400:
                return None, str(response.url), response.status_code

            return response.text, str(response.url), response.status_code

        except Exception:
            return None, None, None

    def _extract_text(self, html: str) -> str | None:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )

        if text and self._word_count(text) >= 80:
            return text.strip()

        yahoo_text = self._extract_yahoo_article_text(html)

        if yahoo_text and self._word_count(yahoo_text) > self._word_count(text):
            return yahoo_text.strip()

        if text:
            return text.strip()

        return None

    def _extract_continue_reading_url(
        self,
        html: str,
        base_url: str,
    ) -> str | None:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Look for visible text links like "Continue reading"
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True).lower()

            if self._is_continue_reading_text(text):
                return urljoin(base_url, anchor["href"])

        # 2. Some pages use aria-label instead of visible text.
        for anchor in soup.find_all("a", href=True):
            aria_label = (anchor.get("aria-label") or "").lower()

            if self._is_continue_reading_text(aria_label):
                return urljoin(base_url, anchor["href"])

        # 3. Some links may have title attributes.
        for anchor in soup.find_all("a", href=True):
            title = (anchor.get("title") or "").lower()

            if self._is_continue_reading_text(title):
                return urljoin(base_url, anchor["href"])

        return None

    def _is_continue_reading_text(self, text: str) -> bool:
        markers = [
            "continue reading",
            "read more",
            "read full article",
            "view full article",
            "full article",
        ]

        return any(marker in text for marker in markers)

    def _extract_canonical_url(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")

        selectors = [
            ("link", {"rel": "canonical"}),
            ("meta", {"property": "og:url"}),
            ("meta", {"name": "parsely-link"}),
            ("meta", {"name": "twitter:url"}),
        ]

        for tag_name, attrs in selectors:
            tag = soup.find(tag_name, attrs=attrs)

            if not tag:
                continue

            if tag_name == "link":
                href = tag.get("href")
                if href:
                    return str(href)

            content = tag.get("content")
            if content:
                return str(content)

        return None

    def _extract_yahoo_article_text(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")

        selectors = [
            "article p",
            "[data-testid='article-body'] p",
            ".caas-body p",
            ".caas-content p",
            ".body p",
        ]

        paragraphs: list[str] = []

        for selector in selectors:
            for node in soup.select(selector):
                text = node.get_text(" ", strip=True)

                if text and text.lower() not in {"story continues"}:
                    paragraphs.append(text)

        cleaned = []
        seen = set()

        for paragraph in paragraphs:
            key = paragraph.lower().strip()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(paragraph)

        result = "\n\n".join(cleaned).strip()

        return result or None

    def _classify_quality(
        self,
        text: str | None,
    ) -> Literal["full", "partial", "metadata_only"]:
        if not text:
            return "metadata_only"

        word_count = self._word_count(text)
        lowered = text.lower()

        bad_markers = [
            "continue reading",
            "read more",
            "subscribe to continue",
            "sign in to continue",
            "enable javascript",
            "please enable js",
            "log in to continue",
            "create a free account",
        ]

        has_bad_marker = any(marker in lowered for marker in bad_markers)

        if word_count >= 250 and not has_bad_marker:
            return "full"

        if word_count >= 80:
            return "partial"

        return "metadata_only"

    def _metadata_only(
        self,
        url: str,
        final_url: str,
        fallback_title: str | None,
        fallback_summary: str | None,
        status: Literal["metadata_only", "blocked", "failed"],
    ) -> ExtractedArticleContent:
        text_parts: list[str] = []

        if fallback_title:
            text_parts.append(f"Title: {fallback_title}")

        if fallback_summary:
            text_parts.append(f"Summary: {fallback_summary}")

        text = "\n".join(text_parts).strip() or None

        return ExtractedArticleContent(
            url=url,
            final_url=final_url,
            title=fallback_title,
            text=text,
            extraction_status=status,
            source_used="metadata",
            word_count=self._word_count(text),
        )

    def _source_type(
        self,
        url: str,
    ) -> Literal["yahoo", "original_source"]:
        domain = urlparse(url).netloc.lower()

        if "yahoo.com" in domain:
            return "yahoo"

        return "original_source"

    def _same_url(
        self,
        left: str | None,
        right: str | None,
    ) -> bool:
        if not left or not right:
            return False

        return left.rstrip("/") == right.rstrip("/")

    def _word_count(self, text: str | None) -> int:
        if not text:
            return 0

        return len(re.findall(r"\b\w+\b", text))