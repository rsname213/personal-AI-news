"""
HTML scrapers for personal blogs that have no working RSS feed.

Each blogger has a dedicated fetch function returning list[RawArticle].
All are fail-soft: any exception returns [] and logs [WARN].

Blogs covered:
  - Andrew Bosworth  (boz.com)          — no dates; relies on dedup for novelty
  - Calvin French-Owen (calv.info)      — dates in <span class="article-date">
  - Max Hodak        (maxhodak.com)     — dates embedded in URL path /YYYY/MM/DD/
"""
import hashlib
import re
from datetime import datetime, timezone, timedelta

import httpx
from bs4 import BeautifulSoup

from models import RawArticle

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; newsletter-bot/1.0)"}
_TIMEOUT = 15
_CUTOFF_HOURS = 169  # 7 days + 1h buffer, same as RSS fetcher


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=_CUTOFF_HOURS)


def _make(url: str, title: str, source: str, published_at: datetime) -> RawArticle:
    return RawArticle(
        id=hashlib.md5(url.encode()).hexdigest(),
        url=url,
        title=title,
        content_text="",
        published_at=published_at,
        source_name=source,
        source_category="Personal Blogs",
    )


# ── Andrew Bosworth ──────────────────────────────────────────────────────────

def fetch_boz() -> list[RawArticle]:
    """
    Scrape boz.com article listing.

    boz.com has no dates in its HTML — articles are timeless essays listed in
    thematic order. We use datetime.now() for all articles so they pass the
    recency filter, and rely on .seen_urls deduplication to avoid re-sending
    articles already delivered. On each run we return only the first article
    found (the newsletter caps to 1 per blogger anyway) so only a new top-listed
    article would slip through after dedup.
    """
    try:
        resp = httpx.get("https://boz.com", headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles: list[RawArticle] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if not href.startswith("/articles/") or len(title) < 5:
                continue
            url = f"https://boz.com{href}"
            articles.append(_make(url, title, "Andrew Bosworth", datetime.now(timezone.utc)))

        return articles

    except Exception as e:
        print(f"[WARN] Andrew Bosworth: fetch failed: {e}")
        return []


# ── Calvin French-Owen ───────────────────────────────────────────────────────

_CALV_DATE_FORMATS = ["%b %d, %Y", "%B %d, %Y"]  # "FEB 17, 2026" or "February 17, 2026"


def _parse_calv_date(text: str) -> datetime | None:
    text = text.strip().upper()
    # Normalize abbreviated month to title case for strptime
    for fmt in ["%b %d, %Y", "%B %d, %Y"]:
        try:
            return datetime.strptime(text.title(), fmt.replace("%b", "%b").replace("%B", "%B")).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    return None


def fetch_calv() -> list[RawArticle]:
    """
    Scrape calv.info article listing.

    HTML structure (verified 2026-03-02):
      Each article block is a <div class="mb-6 ..."> containing:
        - <h2> → <a href="slug"> with article title
        - <span class="article-date"> with date like "FEB 17, 2026"
    """
    cutoff = _cutoff()
    try:
        resp = httpx.get("https://calv.info/", headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles: list[RawArticle] = []
        for date_span in soup.find_all("span", class_="article-date"):
            published_at = _parse_calv_date(date_span.get_text())
            if published_at is None or published_at < cutoff:
                continue

            # Walk up to the shared container then find the article link
            container = date_span.parent
            while container and container.name not in ("div", "article", "li"):
                container = container.parent
            if container is None:
                continue

            a_tag = container.find("a", href=True)
            if not a_tag:
                continue

            href = a_tag["href"]
            title = a_tag.get_text(strip=True)
            if not title:
                continue

            # Resolve relative URLs
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"https://calv.info{href}"
            else:
                url = f"https://calv.info/{href}"

            articles.append(_make(url, title, "Calvin French-Owen", published_at))

        return articles

    except Exception as e:
        print(f"[WARN] Calvin French-Owen: fetch failed: {e}")
        return []


# ── Max Hodak ────────────────────────────────────────────────────────────────

_HODAK_URL_DATE = re.compile(r"/writings/(\d{4})/(\d{2})/(\d{2})/")


def fetch_maxhodak() -> list[RawArticle]:
    """
    Scrape maxhodak.com/writings/ article listing.

    HTML structure (verified 2026-03-02):
      Links in format /writings/YYYY/MM/DD/slug — date parsed directly from URL.
    """
    cutoff = _cutoff()
    try:
        resp = httpx.get(
            "https://maxhodak.com/writings/",
            headers=_HEADERS,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles: list[RawArticle] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            m = _HODAK_URL_DATE.search(href)
            if not m or len(title) < 5:
                continue

            published_at = datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                tzinfo=timezone.utc,
            )
            if published_at < cutoff:
                continue

            url = f"https://maxhodak.com{href}" if href.startswith("/") else href
            articles.append(_make(url, title, "Max Hodak", published_at))

        return articles

    except Exception as e:
        print(f"[WARN] Max Hodak: fetch failed: {e}")
        return []
