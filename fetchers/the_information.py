"""
The Information fetcher via Google News RSS.

The Information's own RSS feed is behind Cloudflare bot protection (403 for
all non-browser clients). Google News indexes their headlines and exposes
them via a public RSS feed with publication dates.

Since The Information is paywalled, article content is unavailable regardless
of approach. Claude summarizes from the headline — sufficient for a digest.
"""
import hashlib
from datetime import datetime, timezone, timedelta

import feedparser

from models import RawArticle

_GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q=site:theinformation.com"
    "&hl=en-US&gl=US&ceid=US:en"
)
_CUTOFF_HOURS = 169  # 7 days + 1h buffer, same as other fetchers


def fetch() -> list[RawArticle]:
    """Fetch The Information headlines from Google News RSS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_CUTOFF_HOURS)

    try:
        feed = feedparser.parse(_GOOGLE_NEWS_RSS)
        articles: list[RawArticle] = []

        for entry in feed.entries:
            # Only keep articles sourced from The Information
            source = entry.get("source", {})
            source_url = getattr(source, "href", "") if hasattr(source, "href") else ""
            if "theinformation.com" not in source_url:
                continue

            if entry.get("published_parsed") is None:
                continue

            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published_at < cutoff:
                continue

            # Clean title: strip " - The Information" suffix
            title = entry.get("title", "")
            title = title.removesuffix(" - The Information").strip()
            if not title:
                continue

            # Use Google News link (redirects to the real article via JS)
            url = entry.get("link", "")

            articles.append(
                RawArticle(
                    id=hashlib.md5(url.encode()).hexdigest(),
                    url=url,
                    title=title,
                    content_text="",  # Paywalled — headline-only summarization
                    published_at=published_at,
                    source_name="The Information",
                    source_category="The Information",
                )
            )

        return articles

    except Exception as e:
        print(f"[WARN] The Information: {e}")
        return []
