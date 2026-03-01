"""
Anthropic Blog fetcher.
Primary: Community-maintained RSS feed (taobojlen/anthropic-rss-feed).
Fallback: Scrape anthropic.com/news if community feed returns 0 articles.

HTML structure of anthropic.com/news (verified 2026-03-01):
  - News cards are <a href="/news/slug"> elements
  - Card text includes date strings like "Feb 27, 2026"
  - First <p> inside the card is typically the article subtitle/description
"""
import hashlib
import re
from datetime import datetime, timezone, timedelta

import httpx
from bs4 import BeautifulSoup

from fetchers.rss import fetch_feed
from models import RawArticle

ANTHROPIC_COMMUNITY_FEED = (
    "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/"
    "anthropic_news_rss.xml"
)
ANTHROPIC_NEWS_URL = "https://www.anthropic.com/news"

# Date pattern found in card text on anthropic.com/news
_DATE_PATTERN = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}"
)


def fetch() -> list[RawArticle]:
    """
    Fetch Anthropic blog posts.

    Tries the community RSS feed first; falls back to scraping anthropic.com/news
    if the feed returns 0 articles.
    """
    articles = fetch_feed(ANTHROPIC_COMMUNITY_FEED, "Anthropic", "Anthropic")
    if articles:
        return articles

    print(
        "[WARN] Anthropic: community feed returned 0 articles — trying direct scrape"
    )
    return _scrape_anthropic_news()


def _scrape_anthropic_news() -> list[RawArticle]:
    """Scrape anthropic.com/news as a fallback source."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)

    try:
        response = httpx.get(
            ANTHROPIC_NEWS_URL,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; newsletter-bot/1.0)"},
        )
        response.raise_for_status()
    except Exception as e:
        print(f"[WARN] Anthropic scrape fallback failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    seen_urls: set[str] = set()
    articles: list[RawArticle] = []

    # Each card is an <a href="/news/slug"> element containing date and title text
    for card in soup.select("a[href*='/news/']"):
        href = card.get("href", "")
        if not href:
            continue

        # Normalize to absolute URL
        if href.startswith("/"):
            href = f"https://www.anthropic.com{href}"

        # Deduplicate (some cards appear twice on the page)
        if href in seen_urls:
            continue
        seen_urls.add(href)

        card_text = card.get_text(separator=" ", strip=True)

        # Extract date from card text (e.g. "Feb 27, 2026")
        date_match = _DATE_PATTERN.search(card_text)
        if date_match:
            try:
                published_at = datetime.strptime(
                    date_match.group(0), "%b %d, %Y"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                published_at = datetime.now(timezone.utc)
        else:
            # Date not found — use now as conservative fallback so article passes filter
            published_at = datetime.now(timezone.utc)

        # Apply 25-hour recency filter
        if published_at < cutoff:
            continue

        # Extract title: prefer first <p> child, fall back to full card text
        title_el = card.select_one("p, h2, h3, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else card_text[:120]
        if not title:
            continue

        articles.append(
            RawArticle(
                id=hashlib.md5(href.encode()).hexdigest(),
                url=href,
                title=title,
                content_text="",
                published_at=published_at,
                source_name="Anthropic",
                source_category="Anthropic",
            )
        )

    print(f"[OK] Anthropic (scraped fallback): {len(articles)} article(s)")
    return articles[:5]  # Cap at 5 for fallback path
