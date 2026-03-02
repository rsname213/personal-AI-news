"""
Generic RSS/Atom fetcher for the AI Newsletter pipeline.

Provides:
  - fetch_feed(feed_url, source_name, source_category) -> list[RawArticle]
  - fetch_all() -> list[RawArticle]
  - FEED_URLS: config dict of all standard sources (18 personal blogs + WSJ)

Feed URLs are MEDIUM confidence — personal bloggers may have moved platforms.
Fix a bad URL directly in FEED_URLS without touching any code logic.
"""
import hashlib
import os
from datetime import datetime, timezone, timedelta

import feedparser

from models import RawArticle

# ---------------------------------------------------------------------------
# Source config — 18 personal blogs + 1 news source = 19 total
# Format: { "Display Name": ("feed_url", "source_category") }
# ---------------------------------------------------------------------------
FEED_URLS: dict[str, tuple[str, str]] = {
    # Personal Blogs
    # Removed (no working RSS): Andrew Bosworth, Ava Huang, Graham Duncan (last post 2018),
    #   Calvin French-Owen, Max Hodak — handled via HTML scrapers in fetchers/blog_scrapers.py
    # Ava Huang: all known URLs (avahu.me, ava.substack.com) fail DNS/Cloudflare
    # Graham Duncan: Cloudflare-blocked + inactive since 2018
    "Ben Kuhn": ("https://www.benkuhn.net/rss/", "Personal Blogs"),
    "Brie Wolfson": ("https://koolaidfactory.com/feed", "Personal Blogs"),  # Kool-Aid Factory
    "Holden Karnofsky": ("https://www.cold-takes.com/rss/", "Personal Blogs"),
    "Henrik Karlsson": ("https://www.henrikkarlsson.xyz/feed", "Personal Blogs"),
    "Justin Meiners": ("https://jmeiners.com/feed.xml", "Personal Blogs"),
    "Kevin Kwok": ("https://kwokchain.com/feed/", "Personal Blogs"),
    "Tyler Cowen": ("https://marginalrevolution.com/feed", "Personal Blogs"),
    "Nabeel Qureshi": ("https://nabeelqu.co/rss", "Personal Blogs"),       # was nabeelqu.substack.com
    "Nadia Asparouhova": ("https://nadia.xyz/feed", "Personal Blogs"),     # was nadia.xyz/rss.xml
    "Sam Altman": ("https://blog.samaltman.com/posts.atom", "Personal Blogs"),
    "Scott Alexander": ("https://www.astralcodexten.com/feed", "Personal Blogs"),  # was substack URL
    "James Somers": ("https://jsomers.net/blog/feed", "Personal Blogs"),   # was jsomers.net/feed.xml (stale 2009)
    "Tom Tunguz": ("https://tomtunguz.com/index.xml", "Personal Blogs"),   # was /feed/
    # News Sources
    "WSJ": (
        os.environ.get("WSJ_RSS_URL", "https://feeds.content.dowjones.io/public/rss/RSSWSJD"),
        "WSJ",
    ),
    "TechCrunch AI": ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch"),
    # The Information: moved to fetchers/the_information.py (Google News RSS)
    # — Cloudflare blocks direct RSS access.
}


def fetch_feed(feed_url: str, source_name: str, source_category: str) -> list[RawArticle]:
    """
    Fetch a single RSS/Atom feed and return recent articles as RawArticle objects.

    - Uses a 169-hour (7d + 1h) cutoff window to cover the full weekly digest window.
    - Entries without a published date are skipped.
    - Any exception is caught, logged as [WARN], and returns [].
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7, hours=1)

    try:
        feed = feedparser.parse(feed_url)

        articles: list[RawArticle] = []
        for entry in feed.entries:
            # Skip entries with no publication date
            if entry.get("published_parsed") is None:
                continue

            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            # Recency filter: 7-day window
            if published_at < cutoff:
                continue

            # Extract content: try full content first, then summary, then empty
            content_text = ""
            if hasattr(entry, "content") and entry.content:
                content_text = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content_text = entry.summary

            url = entry.get("link", "")

            articles.append(
                RawArticle(
                    id=hashlib.md5(url.encode()).hexdigest(),
                    url=url,
                    title=entry.get("title", ""),
                    content_text=content_text,
                    published_at=published_at,
                    source_name=source_name,
                    source_category=source_category,
                )
            )

        return articles

    except Exception as e:
        print(f"[WARN] {source_name}: {e}")
        return []


def fetch_all() -> list[RawArticle]:
    """
    Fetch all configured sources and return a flat list of RawArticle.

    Each source is fetched independently; failures log [WARN] and are skipped.
    Sources with 0 articles also log a feed health warning.
    """
    all_articles: list[RawArticle] = []

    for source_name, (feed_url, category) in FEED_URLS.items():
        articles = fetch_feed(feed_url, source_name, category)
        count = len(articles)
        print(f"[OK] {source_name}: {count} article(s)")
        if count == 0:
            print(f"[WARN] {source_name}: returned 0 articles — check feed health")
        all_articles.extend(articles)

    return all_articles
