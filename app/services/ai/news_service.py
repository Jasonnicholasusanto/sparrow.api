import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.news import ExtractedArticleContent, SummarizeArticleResponse


class NewsAIService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client()

    async def summarize_article(
        self,
        url: str,
        extracted: ExtractedArticleContent,
        title: str | None = None,
        source: str | None = None,
    ) -> SummarizeArticleResponse:
        prompt = f"""
            You are Sparrow's financial news analyst.

            You are summarizing a news article for a retail investor.

            Extraction status: {extracted.extraction_status}
            Source used: {extracted.source_used}
            Word count: {extracted.word_count}

            Important rules:
            - If extraction_status is "full", summarize normally.
            - If extraction_status is "partial", say the summary is based on the available excerpt.
            - If extraction_status is "metadata_only", only summarize what can be inferred from the title/source/metadata.
            - Do not pretend you read the full article.
            - Do not invent details.
            - Keep it useful but cautious.

            Title: {title}
            URL: {url}
            Source: {source}

            Available article text:
            {extracted.text[:12000] if extracted.text else ""}
        """

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text or "{}"
        data = json.loads(raw_text)

        return SummarizeArticleResponse(
            url=url,
            summary=data["summary"],
            sentiment_label=data["sentiment_label"],
            sentiment_score=float(data["sentiment_score"]),
            key_points=data.get("key_points", []),
        )