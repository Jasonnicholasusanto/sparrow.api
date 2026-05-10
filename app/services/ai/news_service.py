import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.news import SummarizeArticleResponse


class NewsAIService:
    def __init__(self) -> None:
        if not settings.GOOGLE_GEMINI_API_KEY:
            raise ValueError("GOOGLE_GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)

    async def summarize_article(
        self,
        url: str,
        article_text: str,
        title: str | None = None,
        source: str | None = None,
    ) -> SummarizeArticleResponse:
        prompt = f"""
You are Sparrow's financial news analyst.

Summarize the article for a retail investor.

Return JSON only with:
- summary: one clear sentence
- sentiment_label: bullish, bearish, or neutral
- sentiment_score: number between -1 and 1
- key_points: max 3 concise bullet points

Rules:
- Be cautious.
- Do not invent facts.
- If the article is macroeconomic or political, use neutral unless there is a clear market impact.
- Keep the summary understandable for beginners.

Title: {title}
Source: {source}
URL: {url}

Article:
{article_text[:12000]}
"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
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