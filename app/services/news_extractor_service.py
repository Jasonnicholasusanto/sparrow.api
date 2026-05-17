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
    "story_continues",
    "continue_reading",
    "canonical",
    "original_source",
    "metadata",
]


class NewsContentExtractor:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    async def _extract_recursive(
        self,
        url: str,
        original_url: str,
        fallback_title: str | None,
        fallback_summary: str | None,
        source_used: SourceUsed | None,
        depth: int,
        visited: set[str],
        max_depth: int = 3,
    ) -> ExtractedArticleContent | None:
        normalized_url = self._normalize_url(url)

        if depth > max_depth or normalized_url in visited:
            return None

        visited.add(normalized_url)

        html, final_url, status_code = await self._fetch_html(url)

        if status_code in {401, 403, 429}:
            return self._metadata_only(
                url=original_url,
                final_url=final_url or url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                status="blocked",
            )

        if not html:
            return None

        base_url = final_url or url

        text = self._extract_text(html)
        quality = self._classify_quality(text)

        resolved_source = source_used or self._source_type(base_url)

        if quality == "full":
            return ExtractedArticleContent(
                url=original_url,
                final_url=base_url,
                title=fallback_title,
                text=text,
                extraction_status="full",
                source_used=resolved_source,
                word_count=self._word_count(text),
            )

        # Yahoo "Story continues" usually means inline/same-page continuation.
        # With httpx, we cannot click JS buttons, but we can attempt to extract
        # any hidden/inline Yahoo article body that is already present in the HTML.
        has_story_continues = self._has_story_continues_marker(html)

        if has_story_continues:
            yahoo_text = self._extract_yahoo_article_text(html)

            if yahoo_text and self._word_count(yahoo_text) > self._word_count(text):
                yahoo_quality = self._classify_quality(yahoo_text)

                if yahoo_quality in {"full", "partial"}:
                    return ExtractedArticleContent(
                        url=original_url,
                        final_url=base_url,
                        title=fallback_title,
                        text=yahoo_text,
                        extraction_status=yahoo_quality,
                        source_used="story_continues",
                        word_count=self._word_count(yahoo_text),
                    )

        # "Continue reading" generally points to the original external publisher.
        continue_reading_urls = self._extract_continue_reading_urls(
            html=html,
            base_url=base_url,
        )

        for continue_url in continue_reading_urls:
            if self._same_url(continue_url, base_url):
                continue

            continue_result = await self._extract_recursive(
                url=continue_url,
                original_url=original_url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                source_used="continue_reading",
                depth=depth + 1,
                visited=visited,
                max_depth=max_depth,
            )

            if continue_result and continue_result.extraction_status in {"full", "partial"}:
                return continue_result

        # Try canonical / og URL recursively.
        canonical_urls = self._extract_canonical_urls(html)

        for canonical_url in canonical_urls:
            canonical_url = urljoin(base_url, canonical_url)

            if self._same_url(canonical_url, base_url):
                continue

            canonical_result = await self._extract_recursive(
                url=canonical_url,
                original_url=original_url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                source_used="canonical",
                depth=depth + 1,
                visited=visited,
                max_depth=max_depth,
            )

            if canonical_result and canonical_result.extraction_status in {"full", "partial"}:
                return canonical_result

        if text:
            return ExtractedArticleContent(
                url=original_url,
                final_url=base_url,
                title=fallback_title,
                text=text,
                extraction_status="partial",
                source_used=resolved_source,
                word_count=self._word_count(text),
            )

        if depth == 0:
            return self._metadata_only(
                url=original_url,
                final_url=base_url,
                fallback_title=fallback_title,
                fallback_summary=fallback_summary,
                status="metadata_only",
            )

        return None

    async def extract_article_content(
        self,
        url: str,
        fallback_title: str | None = None,
        fallback_summary: str | None = None,
    ) -> ExtractedArticleContent:
        """
        Recursive extraction flow:

        1. Try extracting from the provided URL.
        2. If page has usable/full content, return it.
        3. If page has "Story continues", try extracting more Yahoo inline content.
        4. If page has "Continue reading", recursively follow the external URL.
        5. If needed, recursively try canonical / og:url / parsely-link.
        6. Fall back to partial text or metadata.
        """

        result = await self._extract_recursive(
            url=url,
            original_url=url,
            fallback_title=fallback_title,
            fallback_summary=fallback_summary,
            source_used=None,
            depth=0,
            visited=set(),
        )

        if result:
            return result

        return self._metadata_only(
            url=url,
            final_url=url,
            fallback_title=fallback_title,
            fallback_summary=fallback_summary,
            status="failed",
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

    def _extract_continue_reading_urls(
        self,
        html: str,
        base_url: str,
    ) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")

        urls: list[str] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            text_parts = [
                anchor.get_text(" ", strip=True),
                anchor.get("aria-label") or "",
                anchor.get("title") or "",
            ]

            combined_text = " ".join(text_parts).lower()

            if not self._is_continue_reading_text(combined_text):
                continue

            href = anchor.get("href")

            if not href:
                continue

            absolute_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(absolute_url)

            if normalized_url in seen:
                continue

            seen.add(normalized_url)
            urls.append(absolute_url)

        return urls

    def _has_story_continues_marker(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")

        marker_texts = [
            "story continues",
            "story continues below",
        ]

        for node in soup.find_all(["button", "a", "span", "div", "p"]):
            text = node.get_text(" ", strip=True).lower()

            if any(marker in text for marker in marker_texts):
                return True

        return False

    def _is_continue_reading_text(self, text: str) -> bool:
        markers = [
            "continue reading",
            "read more",
            "read full article",
            "view full article",
            "full article",
            "continue to article",
            "read the full story",
        ]

        return any(marker in text for marker in markers)

    def _extract_canonical_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")

        candidates: list[str] = []
        seen: set[str] = set()

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

            value = None

            if tag_name == "link":
                value = tag.get("href")
            else:
                value = tag.get("content")

            if not value:
                continue

            normalized = self._normalize_url(str(value))

            if normalized in seen:
                continue

            seen.add(normalized)
            candidates.append(str(value))

        return candidates

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")

        return f"{scheme}://{netloc}{path}"

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

        return self._normalize_url(left) == self._normalize_url(right)

    def _word_count(self, text: str | None) -> int:
        if not text:
            return 0

        return len(re.findall(r"\b\w+\b", text))