"""
Paul Graham fetcher.
Primary: Community-maintained RSS feed (olshansk/pgessays-rss, updated nightly).
The official paulgraham.com RSS has been broken since October 2023.
"""
import feedparser

from fetchers.rss import fetch_feed

PG_COMMUNITY_FEED = (
    "https://raw.githubusercontent.com/olshansk/pgessays-rss/main/feed.xml"
)


def fetch() -> list:
    """Fetch Paul Graham essays via community RSS feed."""
    return fetch_feed(PG_COMMUNITY_FEED, "Paul Graham", "Personal Blogs")
