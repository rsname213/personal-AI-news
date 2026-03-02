"""
Gwern Branwen fetcher.
Scrapes gwern.net/blog/index — no native RSS exists (GitHub issue #11, open since 2015).

HTML structure (verified against live page 2026-03-01):
  - Page contains <section class="level1" id="YYYY"> elements per year
  - Inside each section, post links have an `id` attribute in YYYY-MM-DD format
    and an `href` like /blog/YYYY/slug
  - Example: <a id="2026-01-22" href="/blog/2026/hutter-prize">Towards a Better Hutter Prize</a>

This gives us precise dates — no year-only approximation needed.
"""
import hashlib
import re
from datetime import datetime, timezone, timedelta

import httpx
from bs4 import BeautifulSoup

from models import RawArticle

GWERN_BLOG_INDEX = "https://gwern.net/blog/index"


def fetch() -> list[RawArticle]:
    """Scrape gwern.net/blog/index and return recent RawArticle items."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7, hours=1)

    try:
        response = httpx.get(
            GWERN_BLOG_INDEX,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; newsletter-bot/1.0)"},
        )
        response.raise_for_status()
    except Exception as e:
        print(f"[WARN] Gwern Branwen: fetch failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    articles: list[RawArticle] = []

    # Each year section has id="YYYY" and contains links with id="YYYY-MM-DD"
    # Strategy: find all <a> elements with id matching the YYYY-MM-DD pattern
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    for link in soup.find_all("a", id=date_pattern):
        link_id = link.get("id", "")  # e.g. "2026-01-22"
        href = link.get("href", "")
        title = link.get_text(strip=True)

        if not href or not title:
            continue

        # Normalize relative URLs
        if href.startswith("/"):
            href = f"https://gwern.net{href}"
        elif not href.startswith("http"):
            continue

        # Parse the precise date from the id attribute
        try:
            published_at = datetime.strptime(link_id, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue

        # Apply 25-hour recency filter
        if published_at < cutoff:
            continue

        articles.append(
            RawArticle(
                id=hashlib.md5(href.encode()).hexdigest(),
                url=href,
                title=title,
                content_text="",  # Not fetched at scrape time — too slow for Phase 1
                published_at=published_at,
                source_name="Gwern Branwen",
                source_category="Personal Blogs",
            )
        )

    print(f"[OK] Gwern Branwen: {len(articles)} article(s)")
    if len(articles) == 0:
        print(
            "[WARN] Gwern Branwen: returned 0 articles"
            " — HTML structure may have changed or no posts in last 7 days"
        )
    return articles
