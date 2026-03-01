"""
Generic RSS/Atom fetcher for the AI Newsletter pipeline.

Provides:
  - fetch_feed(feed_url, source_name, source_category) -> list[RawArticle]
  - fetch_all() -> list[RawArticle]
  - FEED_URLS: config dict of all standard sources (18 personal blogs + WSJ + The Information)

Feed URLs are MEDIUM confidence — personal bloggers may have moved platforms.
Fix a bad URL directly in FEED_URLS without touching any code logic.
"""
import hashlib
from datetime import datetime, timezone, timedelta

import feedparser

from models import RawArticle

# ---------------------------------------------------------------------------
# Source config — 18 personal blogs + 2 news sources = 20 total
# Format: { "Display Name": ("feed_url", "source_category") }
# ---------------------------------------------------------------------------
FEED_URLS: dict[str, tuple[str, str]] = {
    # Personal Blogs
    "Andrew Bosworth": ("https://boz.com/feed", "Personal Blogs"),
    "Ben Kuhn": ("https://www.benkuhn.net/rss/", "Personal Blogs"),
    "Ava Huang": ("https://avahu.substack.com/feed", "Personal Blogs"),
    "Brie Wolfson": ("https://www.briewolfson.com/feed", "Personal Blogs"),
    "Calvin French-Owen": ("https://calv.info/rss.xml", "Personal Blogs"),
    "Holden Karnofsky": ("https://www.cold-takes.com/rss/", "Personal Blogs"),
    "Graham Duncan": ("https://grahambduncan.substack.com/feed", "Personal Blogs"),
    "Henrik Karlsson": ("https://www.henrikkarlsson.xyz/feed", "Personal Blogs"),
    "Justin Meiners": ("https://jmeiners.com/feed.xml", "Personal Blogs"),
    "James Somers": ("https://jsomers.net/feed.xml", "Personal Blogs"),
    "Kevin Kwok": ("https://kwokchain.com/feed/", "Personal Blogs"),
    "Tyler Cowen": ("https://marginalrevolution.com/feed", "Personal Blogs"),
    "Max Hodak": ("https://maxhodak.substack.com/feed", "Personal Blogs"),
    "Nabeel Qureshi": ("https://nabeelqu.substack.com/feed", "Personal Blogs"),
    "Nadia Asparouhova": ("https://nadia.xyz/rss.xml", "Personal Blogs"),
    "Sam Altman": ("https://blog.samaltman.com/posts.atom", "Personal Blogs"),
    "Scott Alexander": ("https://astralcodexten.substack.com/feed/", "Personal Blogs"),
    "Tom Tunguz": ("https://tomtunguz.com/feed/", "Personal Blogs"),
    # News Sources
    "WSJ": ("https://feeds.a.wsj.com/rss/RSSWSJD.xml", "WSJ"),
    "The Information": ("https://www.theinformation.com/feed", "The Information"),
}


def fetch_feed(feed_url: str, source_name: str, source_category: str) -> list[RawArticle]:
    """
    Fetch a single RSS/Atom feed and return recent articles as RawArticle objects.

    - Uses a 25-hour cutoff window (not 24h) to absorb GitHub Actions scheduling delays.
    - Entries without a published date are skipped.
    - Any exception is caught, logged as [WARN], and returns [].
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=25)

    try:
        feed = feedparser.parse(feed_url)

        # Special handling for The Information — warn if feed appears empty or broken
        if source_name == "The Information":
            if getattr(feed, "bozo", False) or len(feed.entries) == 0:
                print(
                    "[WARN] The Information: feed may require subscriber authentication"
                    " — treating as empty for Phase 1"
                )
                return []

        articles: list[RawArticle] = []
        for entry in feed.entries:
            # Skip entries with no publication date
            if entry.get("published_parsed") is None:
                continue

            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            # Recency filter: 25-hour window
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
